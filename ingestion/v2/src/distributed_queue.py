"""Distributed Queue Abstraction - Redis or In-Memory Implementation"""
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QueuedItem:
    """Item in the ingestion queue."""
    id: str
    data: Dict[str, Any]
    priority: int = 0  # Higher = process first
    created_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """Check if item can be retried."""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


class BaseQueue(ABC):
    """Abstract base for ingestion queue implementations."""
    
    @abstractmethod
    async def enqueue(self, item: QueuedItem) -> bool:
        """Add item to queue."""
        pass
    
    @abstractmethod
    async def dequeue(self) -> Optional[QueuedItem]:
        """Remove and return next item from queue."""
        pass
    
    @abstractmethod
    async def peek(self) -> Optional[QueuedItem]:
        """Look at next item without removing it."""
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """Get current queue size."""
        pass
    
    @abstractmethod
    async def mark_processing(self, item_id: str) -> bool:
        """Mark item as being processed (prevent loss)."""
        pass
    
    @abstractmethod
    async def mark_complete(self, item_id: str) -> bool:
        """Mark item as completed."""
        pass
    
    @abstractmethod
    async def requeue_failed(self, item: QueuedItem) -> bool:
        """Requeue a failed item, incrementing retry count."""
        pass
    
    @abstractmethod
    async def clear(self):
        """Clear all items from queue."""
        pass


class InMemoryQueue(BaseQueue):
    """In-memory queue implementation (local/development)."""
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize in-memory queue.
        
        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self.processing: Dict[str, QueuedItem] = {}  # Items being processed
    
    async def enqueue(self, item: QueuedItem) -> bool:
        """Add item to queue (priority queue: higher priority processed first)."""
        try:
            # Use negative priority for max-heap behavior
            await asyncio.wait_for(
                self.queue.put((-item.priority, item.id, item)),
                timeout=1.0
            )
            return True
        except asyncio.TimeoutError:
            return False
    
    async def dequeue(self) -> Optional[QueuedItem]:
        """Remove and return next item."""
        try:
            _, item_id, item = await asyncio.wait_for(
                self.queue.get(),
                timeout=0.5
            )
            self.processing[item.id] = item
            return item
        except asyncio.TimeoutError:
            return None
    
    async def peek(self) -> Optional[QueuedItem]:
        """Look at next item without removing."""
        if not self.queue.empty():
            _, item_id, item = self.queue._queue[0]
            return item
        return None
    
    async def size(self) -> int:
        """Get queue + processing size."""
        return self.queue.qsize() + len(self.processing)
    
    async def mark_processing(self, item_id: str) -> bool:
        """Mark item as processing (already done on dequeue)."""
        return item_id in self.processing
    
    async def mark_complete(self, item_id: str) -> bool:
        """Remove item from processing."""
        if item_id in self.processing:
            del self.processing[item_id]
            return True
        return False
    
    async def requeue_failed(self, item: QueuedItem) -> bool:
        """Requeue a failed item."""
        if item.can_retry():
            item.retry_count += 1
            return await self.enqueue(item)
        return False
    
    async def clear(self):
        """Clear queue and processing items."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.processing.clear()


class RedisQueue(BaseQueue):
    """Redis-backed queue implementation (production)."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "era_ingestion"):
        """
        Initialize Redis queue.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for this queue
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self.redis = None  # Will be set by async init
        self.queue_key = f"{prefix}:queue"
        self.processing_key = f"{prefix}:processing"
        self.completed_key = f"{prefix}:completed"
    
    async def init(self):
        """Initialize Redis connection (call after create)."""
        try:
            import aioredis
            self.redis = await aioredis.create_redis_pool(self.redis_url)
        except ImportError:
            raise ImportError("aioredis required for RedisQueue. Install: pip install aioredis")
    
    async def enqueue(self, item: QueuedItem) -> bool:
        """Add item to Redis queue."""
        if not self.redis:
            await self.init()
        try:
            item_json = json.dumps(item.to_dict())
            # Add with score = -priority (for sorted set with reverse ordering)
            await self.redis.zadd(self.queue_key, -item.priority, item.id)
            await self.redis.set(f"{self.prefix}:item:{item.id}", item_json)
            return True
        except Exception as e:
            print(f"Error enqueuing item: {e}")
            return False
    
    async def dequeue(self) -> Optional[QueuedItem]:
        """Remove and return next item from Redis."""
        if not self.redis:
            await self.init()
        try:
            # Get highest priority item (lowest score due to -priority)
            items = await self.redis.zrange(self.queue_key, 0, 0)
            if not items:
                return None
            
            item_id = items[0].decode() if isinstance(items[0], bytes) else items[0]
            item_json = await self.redis.get(f"{self.prefix}:item:{item_id}")
            
            if not item_json:
                return None
            
            item_data = json.loads(item_json)
            item = QueuedItem(**item_data)
            
            # Move to processing
            await self.redis.zrem(self.queue_key, item_id)
            await self.redis.zadd(self.processing_key, 0, item_id)
            
            return item
        except Exception as e:
            print(f"Error dequeueing item: {e}")
            return None
    
    async def peek(self) -> Optional[QueuedItem]:
        """Look at next item without removing."""
        if not self.redis:
            await self.init()
        try:
            items = await self.redis.zrange(self.queue_key, 0, 0)
            if not items:
                return None
            
            item_id = items[0].decode() if isinstance(items[0], bytes) else items[0]
            item_json = await self.redis.get(f"{self.prefix}:item:{item_id}")
            
            if not item_json:
                return None
            
            return QueuedItem(**json.loads(item_json))
        except Exception:
            return None
    
    async def size(self) -> int:
        """Get queue + processing size."""
        if not self.redis:
            await self.init()
        try:
            queue_size = await self.redis.zcard(self.queue_key)
            processing_size = await self.redis.zcard(self.processing_key)
            return queue_size + processing_size
        except Exception:
            return 0
    
    async def mark_processing(self, item_id: str) -> bool:
        """Check if item is processing."""
        if not self.redis:
            await self.init()
        try:
            score = await self.redis.zscore(self.processing_key, item_id)
            return score is not None
        except Exception:
            return False
    
    async def mark_complete(self, item_id: str) -> bool:
        """Mark item as completed."""
        if not self.redis:
            await self.init()
        try:
            await self.redis.zrem(self.processing_key, item_id)
            await self.redis.zadd(self.completed_key, 0, item_id)
            return True
        except Exception:
            return False
    
    async def requeue_failed(self, item: QueuedItem) -> bool:
        """Requeue a failed item."""
        if not self.redis:
            await self.init()
        try:
            if item.can_retry():
                item.retry_count += 1
                return await self.enqueue(item)
            else:
                # Move to dead-letter queue
                await self.redis.zrem(self.processing_key, item.id)
                await self.redis.zadd(f"{self.prefix}:deadletter", 0, item.id)
                return False
        except Exception:
            return False
    
    async def clear(self):
        """Clear all items."""
        if not self.redis:
            await self.init()
        try:
            await self.redis.delete(self.queue_key)
            await self.redis.delete(self.processing_key)
        except Exception:
            pass


def create_queue(queue_type: str = "memory", **kwargs) -> BaseQueue:
    """
    Factory function to create queue instance.
    
    Args:
        queue_type: "memory" or "redis"
        **kwargs: Additional arguments for queue constructor
        
    Returns:
        Queue instance
    """
    if queue_type == "redis":
        return RedisQueue(**kwargs)
    else:
        return InMemoryQueue(**kwargs)


# Example usage
async def example_queue():
    """Example: Using queue."""
    queue = InMemoryQueue()
    
    # Enqueue items
    for i in range(5):
        item = QueuedItem(
            id=f"item_{i}",
            data={"chapter": i, "book": "test"},
            priority=i % 3
        )
        await queue.enqueue(item)
    
    print(f"Queue size: {await queue.size()}")
    
    # Dequeue items
    while True:
        item = await queue.dequeue()
        if not item:
            break
        print(f"Processing: {item.id}")
        await queue.mark_complete(item.id)


if __name__ == "__main__":
    asyncio.run(example_queue())
