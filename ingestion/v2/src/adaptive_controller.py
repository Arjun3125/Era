"""Adaptive Rate Controller - Token Bucket with Feedback Loop"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque


@dataclass
class RateLimit:
    """Rate limit token bucket configuration."""
    tokens_per_second: float = 100.0
    max_burst: float = 500.0  # Max tokens that can accumulate
    refill_interval: float = 0.1  # Refill tokens every 100ms


@dataclass
class AdaptiveConfig:
    """Adaptive rate control configuration."""
    base_rate_limit: RateLimit = field(default_factory=RateLimit)
    congestion_threshold: float = 0.8  # Queue depth > 80% triggers slowdown
    recovery_threshold: float = 0.3  # Queue depth < 30% triggers speedup
    backpressure_factor: float = 0.5  # Reduce rate by 50% under congestion
    recovery_factor: float = 1.2  # Increase rate by 20% during recovery
    max_rate_multiplier: float = 2.0  # Don't exceed 2x base rate
    min_rate_multiplier: float = 0.2  # Don't drop below 20% of base rate
    feedback_window: int = 100  # Samples to evaluate for feedback adjustment


@dataclass
class PipelineMetrics:
    """Real-time pipeline metrics."""
    processed_items: int = 0
    failed_items: int = 0
    queue_depth: int = 0
    max_queue_depth: int = 0
    avg_processing_time: float = 0.0
    throughput_items_per_sec: float = 0.0
    current_rate_multiplier: float = 1.0
    tokens_available: float = 0.0
    last_update: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        self.last_update = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting."""
        return {
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "queue_depth": self.queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "avg_processing_time_ms": round(self.avg_processing_time * 1000, 2),
            "throughput_items_per_sec": round(self.throughput_items_per_sec, 2),
            "current_rate_multiplier": round(self.current_rate_multiplier, 2),
            "tokens_available": round(self.tokens_available, 2),
            "last_update": self.last_update.isoformat()
        }


class TokenBucket:
    """Token bucket for rate limiting with adaptive feedback."""
    
    def __init__(self, config: RateLimit):
        """
        Initialize token bucket.
        
        Args:
            config: RateLimit configuration
        """
        self.config = config
        self.tokens = config.max_burst  # Start with full burst capacity
        self.last_refill = time.time()
        self.rate_multiplier = 1.0  # Adaptive multiplier
    
    def set_rate_multiplier(self, multiplier: float):
        """Adjust token generation rate (1.0 = normal, 0.5 = half speed, 2.0 = double)."""
        self.rate_multiplier = max(0.1, min(10.0, multiplier))
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens: tps * multiplier * elapsed time
        tokens_to_add = self.config.tokens_per_second * self.rate_multiplier * elapsed
        self.tokens = min(self.config.max_burst, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def acquire(self, tokens_needed: float = 1.0) -> bool:
        """
        Try to acquire tokens. Blocks if not enough tokens.
        
        Args:
            tokens_needed: Number of tokens required
            
        Returns:
            True if tokens acquired, False if timeout
        """
        wait_time = 0.0
        max_wait = 60.0  # Max 60 second wait
        
        while wait_time < max_wait:
            self._refill()
            
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            
            # Calculate wait time for next refill cycle
            tokens_needed_after = tokens_needed - self.tokens
            refill_rate = self.config.tokens_per_second * self.rate_multiplier
            
            if refill_rate > 0:
                wait_seconds = tokens_needed_after / refill_rate
                wait_time += wait_seconds
                await asyncio.sleep(min(wait_seconds, self.config.refill_interval))
            else:
                await asyncio.sleep(self.config.refill_interval)
        
        return False
    
    def current_tokens(self) -> float:
        """Return current token count without refilling."""
        return self.tokens


class AdaptiveController:
    """Adaptive rate controller with feedback loop."""
    
    def __init__(self, config: Optional[AdaptiveConfig] = None):
        """
        Initialize adaptive controller.
        
        Args:
            config: AdaptiveConfig or None for defaults
        """
        self.config = config or AdaptiveConfig()
        self.bucket = TokenBucket(self.config.base_rate_limit)
        self.metrics = PipelineMetrics()
        
        # Feedback tracking
        self.processing_times = deque(maxlen=self.config.feedback_window)
        self.queue_depths = deque(maxlen=self.config.feedback_window)
        self.last_feedback_adjustment = time.time()
        self.feedback_interval = 5.0  # Adjust rate every 5 seconds
    
    async def acquire_permit(self, tokens: float = 1.0) -> bool:
        """
        Acquire rate limit permit. Blocks until available.
        
        Args:
            tokens: Number of tokens to acquire (1 token = 1 typical item)
            
        Returns:
            True if permit acquired
        """
        return await self.bucket.acquire(tokens)
    
    def record_processing(self, processing_time: float, success: bool = True):
        """
        Record item processing result.
        
        Args:
            processing_time: Time in seconds to process item
            success: Whether processing succeeded
        """
        self.processing_times.append(processing_time)
        self.metrics.processed_items += 1
        if not success:
            self.metrics.failed_items += 1
        
        # Update average processing time
        if self.processing_times:
            self.metrics.avg_processing_time = sum(self.processing_times) / len(self.processing_times)
    
    def update_queue_depth(self, depth: int, max_depth: int):
        """
        Update queue depth metrics.
        
        Args:
            depth: Current queue depth
            max_depth: Max queue size
        """
        self.metrics.queue_depth = depth
        self.metrics.max_queue_depth = max(self.metrics.max_queue_depth, depth)
        self.queue_depths.append(depth / max_depth if max_depth > 0 else 0)
        
        # Update tokens available
        self.bucket._refill()
        self.metrics.tokens_available = self.bucket.current_tokens()
    
    def _evaluate_feedback(self):
        """Evaluate queue depth and adjust rate multiplier."""
        if not self.queue_depths:
            return
        
        # Calculate average queue utilization over last window
        avg_utilization = sum(self.queue_depths) / len(self.queue_depths)
        
        # Adjust rate based on congestion
        if avg_utilization > self.config.congestion_threshold:
            # Reduce rate under congestion
            new_multiplier = self.metrics.current_rate_multiplier * self.config.backpressure_factor
        elif avg_utilization < self.config.recovery_threshold:
            # Increase rate during recovery
            new_multiplier = self.metrics.current_rate_multiplier * self.config.recovery_factor
        else:
            return  # No adjustment needed
        
        # Clamp multiplier
        new_multiplier = max(
            self.config.min_rate_multiplier,
            min(self.config.max_rate_multiplier, new_multiplier)
        )
        
        self.metrics.current_rate_multiplier = new_multiplier
        self.bucket.set_rate_multiplier(new_multiplier)
    
    async def feedback_loop(self):
        """
        Continuous feedback loop that adjusts rate based on queue depth.
        Run this in background: asyncio.create_task(controller.feedback_loop())
        """
        while True:
            await asyncio.sleep(self.feedback_interval)
            self._evaluate_feedback()
            
            # Log metrics periodically
            now = datetime.utcnow()
            self.metrics.last_update = now
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return self.metrics.to_dict()
    
    def reset_metrics(self):
        """Reset all metrics counters."""
        self.metrics = PipelineMetrics()
        self.processing_times.clear()
        self.queue_depths.clear()


# Example usage
async def example_controller():
    """Example: Using adaptive controller."""
    config = AdaptiveConfig()
    controller = AdaptiveController(config)
    
    # Start feedback loop
    feedback_task = asyncio.create_task(controller.feedback_loop())
    
    try:
        # Simulate acquiring permits
        for i in range(10):
            if await controller.acquire_permit(tokens=1.0):
                print(f"Item {i}: permit acquired")
                
                # Simulate processing
                await asyncio.sleep(0.1)
                controller.record_processing(0.1, success=True)
                
                # Simulate queue depth
                controller.update_queue_depth(i % 5, max_depth=10)
                
                if i % 3 == 0:
                    print(f"Metrics: {controller.get_metrics()}")
            else:
                print(f"Item {i}: permit timeout")
    finally:
        feedback_task.cancel()


if __name__ == "__main__":
    asyncio.run(example_controller())
