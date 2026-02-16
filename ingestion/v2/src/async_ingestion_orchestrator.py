"""Async Ingestion Orchestrator - Production Pipeline Orchestration"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import uuid

from adaptive_controller import AdaptiveController, AdaptiveConfig
from distributed_queue import BaseQueue, InMemoryQueue, QueuedItem
from ingest_workers import (
    PipelineOrchestrator, WorkerStage, PipelineWorker,
    example_chunk_worker, example_embed_worker, example_store_worker
)


class IngestionPhase(Enum):
    """Ingestion pipeline phase."""
    QUEUED = "queued"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    AGGREGATION = "aggregation"
    STORAGE = "storage"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class IngestionJob:
    """Single ingestion job metadata."""
    job_id: str
    book_slug: str
    chapter_index: int
    text: str
    phase: IngestionPhase = IngestionPhase.QUEUED
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "book_slug": self.book_slug,
            "chapter_index": self.chapter_index,
            "phase": self.phase.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "has_result": self.result is not None,
            "error": self.error
        }


@dataclass
class IngestionMetrics:
    """Overall ingestion metrics."""
    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_processing_time: float = 0.0
    start_time: datetime = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.utcnow()
    
    @property
    def throughput(self) -> float:
        """Items per second."""
        elapsed = (self.end_time or datetime.utcnow() - self.start_time).total_seconds()
        return self.total_completed / elapsed if elapsed > 0 else 0
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful completions."""
        total = self.total_completed + self.total_failed
        return (self.total_completed / total * 100) if total > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_submitted": self.total_submitted,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_processing_time_seconds": round(self.total_processing_time, 2),
            "throughput_items_per_sec": round(self.throughput, 2),
            "success_rate_percent": round(self.success_rate, 2),
            "duration_seconds": round((self.end_time or datetime.utcnow() - self.start_time).total_seconds(), 2)
        }


class AsyncIngestionOrchestrator:
    """Production async ingestion orchestrator with rate control."""
    
    def __init__(
        self,
        queue: Optional[BaseQueue] = None,
        adaptive_config: Optional[AdaptiveConfig] = None,
        chunk_workers: int = 4,
        embed_workers: int = 4,
        store_workers: int = 4,
        max_queue_depth: int = 1000
    ):
        """
        Initialize orchestrator.
        
        Args:
            queue: BaseQueue instance (defaults to InMemoryQueue)
            adaptive_config: AdaptiveConfig for rate control
            chunk_workers: Number of chunking workers
            embed_workers: Number of embedding workers
            store_workers: Number of storage workers
            max_queue_depth: Maximum queue depth for backpressure
        """
        self.queue = queue or InMemoryQueue(max_size=max_queue_depth)
        self.controller = AdaptiveController(adaptive_config or AdaptiveConfig())
        self.max_queue_depth = max_queue_depth
        
        # Pipeline orchestrator
        self.pipeline = PipelineOrchestrator()
        self.pipeline.add_stage(
            WorkerStage.CHUNK,
            example_chunk_worker,
            num_workers=chunk_workers,
            batch_size=10
        )
        self.pipeline.add_stage(
            WorkerStage.EMBED,
            example_embed_worker,
            num_workers=embed_workers,
            batch_size=5
        )
        self.pipeline.add_stage(
            WorkerStage.STORE,
            example_store_worker,
            num_workers=store_workers,
            batch_size=4
        )
        
        # Job tracking
        self.jobs: Dict[str, IngestionJob] = {}
        self.metrics = IngestionMetrics()
        self.running = False
        self.background_tasks = []
    
    async def start(self):
        """Start orchestrator and all subsystems."""
        self.running = True
        self.metrics = IngestionMetrics()
        
        # Start pipeline
        await self.pipeline.start()
        
        # Start feedback loop
        feedback_task = asyncio.create_task(self.controller.feedback_loop())
        self.background_tasks.append(feedback_task)
        
        # Start ingestion loop
        ingest_task = asyncio.create_task(self._ingestion_loop())
        self.background_tasks.append(ingest_task)
    
    async def stop(self):
        """Stop orchestrator."""
        self.running = False
        self.metrics.end_time = datetime.utcnow()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to finish
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Stop pipeline
        await self.pipeline.stop()
    
    async def submit_job(
        self,
        book_slug: str,
        chapter_index: int,
        text: str,
        priority: int = 0
    ) -> str:
        """
        Submit ingestion job.
        
        Args:
            book_slug: Source book identifier
            chapter_index: Chapter number
            text: Chapter text to ingest
            priority: Job priority (higher = process first)
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            book_slug=book_slug,
            chapter_index=chapter_index,
            text=text
        )
        self.jobs[job_id] = job
        
        # Create queued item
        queued_item = QueuedItem(
            id=job_id,
            data={
                "job_id": job_id,
                "book_slug": book_slug,
                "chapter_index": chapter_index,
                "text": text
            },
            priority=priority
        )
        
        # Enqueue
        success = await self.queue.enqueue(queued_item)
        if success:
            self.metrics.total_submitted += 1
            return job_id
        else:
            job.phase = IngestionPhase.FAILED
            job.error = "Failed to enqueue item"
            return job_id
    
    async def _ingestion_loop(self):
        """Main ingestion processing loop."""
        while self.running:
            try:
                # Check queue depth for backpressure
                queue_size = await self.queue.size()
                self.controller.update_queue_depth(queue_size, self.max_queue_depth)
                
                # Acquire rate limit permit
                if not await self.controller.acquire_permit(tokens=1.0):
                    await asyncio.sleep(0.1)
                    continue
                
                # Dequeue item
                queued_item = await self.queue.dequeue()
                if not queued_item:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process through pipeline
                job_id = queued_item.data["job_id"]
                job = self.jobs.get(job_id)
                
                if job:
                    job.phase = IngestionPhase.CHUNKING
                
                try:
                    start_time = time.time()
                    
                    # Process through pipeline
                    result = await self.pipeline.process_item(queued_item.data)
                    
                    elapsed = time.time() - start_time
                    
                    if result and job:
                        job.phase = IngestionPhase.COMPLETE
                        job.result = result
                        job.completed_at = datetime.utcnow()
                        self.metrics.total_completed += 1
                        self.metrics.total_processing_time += elapsed
                        self.controller.record_processing(elapsed, success=True)
                        
                        # Mark as complete
                        await self.queue.mark_complete(job_id)
                    else:
                        raise Exception("Pipeline processing returned None")
                
                except Exception as e:
                    if job:
                        job.phase = IngestionPhase.FAILED
                        job.error = str(e)
                        self.metrics.total_failed += 1
                    
                    self.controller.record_processing(0, success=False)
                    
                    # Try to requeue for retry
                    if queued_item.can_retry():
                        success = await self.queue.requeue_failed(queued_item)
                        if not success and job:
                            job.error += " (all retries exhausted)"
                
            except Exception as e:
                print(f"Ingestion loop error: {e}")
                await asyncio.sleep(0.1)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all job statuses."""
        return [job.to_dict() for job in self.jobs.values()]
    
    def get_orchestrator_metrics(self) -> Dict[str, Any]:
        """Get overall orchestrator metrics."""
        return {
            "ingestion": self.metrics.to_dict(),
            "rate_controller": self.controller.get_metrics(),
            "pipeline": self.pipeline.get_all_metrics()
        }
    
    async def wait_for_completion(self, timeout: float = 300.0) -> bool:
        """
        Wait for all submitted jobs to complete.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if all jobs completed, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.metrics.total_completed + self.metrics.total_failed >= self.metrics.total_submitted:
                return True
            await asyncio.sleep(0.5)
        return False


# Example usage
async def example_orchestrator():
    """Example: Using async orchestrator."""
    orchestrator = AsyncIngestionOrchestrator(
        chunk_workers=2,
        embed_workers=2,
        store_workers=2
    )
    
    await orchestrator.start()
    
    try:
        # Submit jobs
        print("Submitting jobs...")
        job_ids = []
        for i in range(5):
            job_id = await orchestrator.submit_job(
                book_slug="test_book",
                chapter_index=i,
                text=f"Chapter {i} content. " * 100,
                priority=i % 3
            )
            job_ids.append(job_id)
            print(f"Submitted job {i}: {job_id}")
        
        # Wait for completion
        print("\nWaiting for processing...")
        completed = await orchestrator.wait_for_completion(timeout=60.0)
        
        if completed:
            print("All jobs completed!")
        else:
            print("Timeout waiting for jobs")
        
        # Get metrics
        metrics = orchestrator.get_orchestrator_metrics()
        print("\nOrchestrator Metrics:")
        print(json.dumps(metrics, indent=2))
        
        # Show job results
        print("\nJob Results:")
        for job in orchestrator.get_all_jobs():
            print(f"  {job['job_id']}: {job['phase']} - {job.get('error', 'OK')}")
    
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(example_orchestrator())
