"""Async Ingestion Workers - Parallel Processing Pipeline"""
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
import json


class WorkerStage(Enum):
    """Pipeline stage identifiers."""
    CHUNK = "chunk"
    EMBED = "embed"
    MINISTER = "minister"
    STORE = "store"


@dataclass
class WorkerMetrics:
    """Per-worker metrics."""
    stage: WorkerStage
    worker_id: int
    items_processed: int = 0
    items_failed: int = 0
    total_processing_time: float = 0.0
    avg_time_per_item: float = 0.0
    last_item_time: float = 0.0
    
    def record_item(self, processing_time: float, success: bool = True):
        """Record item processing result."""
        if success:
            self.items_processed += 1
        else:
            self.items_failed += 1
        self.total_processing_time += processing_time
        self.last_item_time = processing_time
        if self.items_processed > 0:
            self.avg_time_per_item = self.total_processing_time / self.items_processed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "worker_id": self.worker_id,
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "total_time_seconds": round(self.total_processing_time, 2),
            "avg_time_per_item_ms": round(self.avg_time_per_item * 1000, 2),
            "last_item_time_ms": round(self.last_item_time * 1000, 2)
        }


class PipelineWorker:
    """Base async worker for pipeline stage."""
    
    def __init__(
        self,
        worker_id: int,
        stage: WorkerStage,
        process_fn: Callable[[Dict[str, Any]], Coroutine],
        batch_size: int = 1
    ):
        """
        Initialize worker.
        
        Args:
            worker_id: Worker identifier
            stage: Pipeline stage this worker handles
            process_fn: Async function(item) -> processed_item
            batch_size: Number of items to batch before processing
        """
        self.worker_id = worker_id
        self.stage = stage
        self.process_fn = process_fn
        self.batch_size = batch_size
        self.metrics = WorkerMetrics(stage=stage, worker_id=worker_id)
        self.running = False
    
    async def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process single item.
        
        Args:
            item: Item data
            
        Returns:
            Processed item or None on failure
        """
        try:
            start = time.time()
            result = await self.process_fn(item)
            elapsed = time.time() - start
            self.metrics.record_item(elapsed, success=True)
            return result
        except Exception as e:
            print(f"Worker {self.worker_id} ({self.stage.value}) error: {e}")
            self.metrics.record_item(0.0, success=False)
            return None
    
    async def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process batch of items in parallel.
        
        Args:
            items: Batch of items
            
        Returns:
            List of processed items
        """
        tasks = [self.process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return [r for r in results if r is not None]


class WorkerPool:
    """Pool of parallel workers processing a pipeline stage."""
    
    def __init__(
        self,
        stage: WorkerStage,
        process_fn: Callable,
        num_workers: int = 4,
        batch_size: int = 1
    ):
        """
        Initialize worker pool.
        
        Args:
            stage: Pipeline stage
            process_fn: Async processing function
            num_workers: Number of parallel workers
            batch_size: Batch size for this stage
        """
        self.stage = stage
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.workers = [
            PipelineWorker(i, stage, process_fn, batch_size)
            for i in range(num_workers)
        ]
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
    
    async def start(self):
        """Start all workers."""
        self.running = True
        for worker in self.workers:
            worker.running = True
        
        # Start worker tasks (batching and processing)
        tasks = [self._worker_loop(worker) for worker in self.workers]
        self.worker_tasks = [asyncio.create_task(t) for t in tasks]
    
    async def stop(self):
        """Stop all workers."""
        self.running = False
        
        # Send stop signals
        for _ in self.workers:
            await self.input_queue.put(None)
        
        # Wait for workers to finish
        if hasattr(self, 'worker_tasks'):
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
    
    async def _worker_loop(self, worker: PipelineWorker):
        """Worker processing loop."""
        batch = []
        
        while self.running:
            try:
                # Collect items for batch
                while len(batch) < worker.batch_size:
                    try:
                        item = await asyncio.wait_for(
                            self.input_queue.get(),
                            timeout=0.5
                        )
                        if item is None:  # Stop signal
                            break
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch if we have items
                if batch:
                    results = await worker.process_batch(batch)
                    for result in results:
                        await self.output_queue.put(result)
                    batch = []
                else:
                    await asyncio.sleep(0.01)
            
            except Exception as e:
                print(f"Worker loop error: {e}")
    
    async def enqueue_item(self, item: Dict[str, Any]):
        """Add item to input queue."""
        await self.input_queue.put(item)
    
    async def dequeue_item(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Get next output item."""
        try:
            return await asyncio.wait_for(self.output_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get metrics from all workers."""
        return [w.metrics.to_dict() for w in self.workers]


class PipelineOrchestrator:
    """Orchestrates multi-stage pipeline with worker pools."""
    
    def __init__(self):
        """Initialize orchestrator."""
        self.stages: Dict[WorkerStage, WorkerPool] = {}
        self.running = False
    
    def add_stage(
        self,
        stage: WorkerStage,
        process_fn: Callable,
        num_workers: int = 4,
        batch_size: int = 1
    ) -> WorkerPool:
        """
        Add processing stage to pipeline.
        
        Args:
            stage: Stage identifier
            process_fn: Async processing function for this stage
            num_workers: Number of parallel workers
            batch_size: Batch size for this stage
            
        Returns:
            The created WorkerPool
        """
        pool = WorkerPool(stage, process_fn, num_workers, batch_size)
        self.stages[stage] = pool
        return pool
    
    async def start(self):
        """Start all worker pools."""
        self.running = True
        for pool in self.stages.values():
            await pool.start()
    
    async def stop(self):
        """Stop all worker pools."""
        self.running = False
        for pool in self.stages.values():
            await pool.stop()
    
    async def process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Push item through entire pipeline.
        
        Args:
            item: Initial item
            
        Returns:
            Final item after all stages
        """
        stages_list = list(self.stages.keys())
        current_item = item
        
        # Push through each stage
        for i, stage in enumerate(stages_list):
            pool = self.stages[stage]
            await pool.enqueue_item(current_item)
            
            # Get output from this stage
            current_item = await pool.dequeue_item(timeout=10.0)
            if current_item is None:
                return None
        
        return current_item
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics from all stages."""
        return {
            stage.value: pool.get_metrics()
            for stage, pool in self.stages.items()
        }


# Example worker implementations
async def example_chunk_worker(item: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Split text into chunks."""
    await asyncio.sleep(0.01)  # Simulate work
    text = item.get("text", "")
    chunks = [text[i:i+100] for i in range(0, len(text), 100)]
    return {**item, "chunks": chunks, "chunk_count": len(chunks)}


async def example_embed_worker(item: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Generate embeddings for chunks."""
    await asyncio.sleep(0.05)  # Simulate embedding work
    chunks = item.get("chunks", [])
    embeddings = [[0.1 * j for j in range(384)] for _ in chunks]  # Fake 384-dim embeddings
    return {**item, "embeddings": embeddings}


async def example_store_worker(item: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Store to database."""
    await asyncio.sleep(0.02)  # Simulate DB write
    return {**item, "stored": True, "status": "completed"}


# Example usage
async def example_pipeline():
    """Example: Using pipeline orchestrator."""
    orchestrator = PipelineOrchestrator()
    
    # Add stages
    orchestrator.add_stage(WorkerStage.CHUNK, example_chunk_worker, num_workers=2, batch_size=5)
    orchestrator.add_stage(WorkerStage.EMBED, example_embed_worker, num_workers=2, batch_size=3)
    orchestrator.add_stage(WorkerStage.STORE, example_store_worker, num_workers=2, batch_size=4)
    
    # Start pipeline
    await orchestrator.start()
    
    try:
        # Process items
        for i in range(5):
            item = {"id": f"doc_{i}", "text": "sample text " * 50}
            result = await orchestrator.process_item(item)
            print(f"Processed item {i}: {result is not None}")
        
        # Let pipeline settle
        await asyncio.sleep(2)
        
        # Get metrics
        metrics = orchestrator.get_all_metrics()
        print("\nPipeline Metrics:")
        print(json.dumps({stage: metrics[stage] for stage in metrics}, indent=2))
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(example_pipeline())
