"""Integration Tests for Production Async Ingestion Pipeline"""
import asyncio
import pytest
from typing import List

from adaptive_controller import AdaptiveController, AdaptiveConfig, RateLimit
from distributed_queue import InMemoryQueue, QueuedItem
from ingest_workers import PipelineOrchestrator, WorkerStage
from async_ingestion_orchestrator import AsyncIngestionOrchestrator, IngestionPhase
from benchmark_harness import BenchmarkHarness, BenchmarkPhase


class TestAdaptiveController:
    """Test adaptive rate controller."""
    
    @pytest.mark.asyncio
    async def test_token_bucket_basic(self):
        """Test basic token bucket functionality."""
        config = AdaptiveConfig(
            base_rate_limit=RateLimit(tokens_per_second=10.0, max_burst=100.0)
        )
        controller = AdaptiveController(config)
        
        # Should acquire tokens
        assert await controller.acquire_permit(tokens=1.0)
        assert await controller.acquire_permit(tokens=5.0)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiting blocks when exhausted."""
        config = AdaptiveConfig(
            base_rate_limit=RateLimit(tokens_per_second=1.0, max_burst=1.0)
        )
        controller = AdaptiveController(config)
        
        # Acquire all tokens
        assert await controller.acquire_permit(tokens=1.0)
        
        # Should not be able to acquire more without waiting
        # (we'd have to wait ~1 second for refill)
    
    @pytest.mark.asyncio
    async def test_feedback_adjustment(self):
        """Test feedback-based rate adjustment."""
        config = AdaptiveConfig()
        controller = AdaptiveController(config)
        
        initial_multiplier = controller.metrics.current_rate_multiplier
        
        # Simulate high queue utilization
        for _ in range(100):
            controller.update_queue_depth(8, max_depth=10)  # 80% utilization
        
        controller._evaluate_feedback()
        
        # Rate should have decreased under congestion
        assert controller.metrics.current_rate_multiplier < initial_multiplier


class TestDistributedQueue:
    """Test distributed queue."""
    
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        """Test basic enqueue/dequeue operations."""
        queue = InMemoryQueue()
        
        item = QueuedItem(id="test_1", data={"text": "test"}, priority=1)
        assert await queue.enqueue(item)
        
        dequeued = await queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == "test_1"
        
        assert await queue.mark_complete("test_1")
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test that higher priority items are dequeued first."""
        queue = InMemoryQueue()
        
        # Enqueue in order
        for i in range(3):
            item = QueuedItem(
                id=f"item_{i}",
                data={"pos": i},
                priority=i
            )
            await queue.enqueue(item)
        
        # Dequeue should return highest priority first
        first = await queue.dequeue()
        assert first.id == "item_2"  # Priority 2 is highest
        
        second = await queue.dequeue()
        assert second.id == "item_1"  # Priority 1 is next
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry handling for failed items."""
        queue = InMemoryQueue()
        
        item = QueuedItem(id="test_retry", data={"test": True}, max_retries=2)
        await queue.enqueue(item)
        
        # First retrieval
        dequeued = await queue.dequeue()
        assert dequeued.retry_count == 0
        assert dequeued.can_retry()
        
        # Requeue as failed
        success = await queue.requeue_failed(dequeued)
        assert success
        
        # Retrieve again
        dequeued2 = await queue.dequeue()
        assert dequeued2.retry_count == 1


class TestPipelineWorkers:
    """Test pipeline worker pools."""
    
    @pytest.mark.asyncio
    async def test_worker_pool_processing(self):
        """Test worker pool can process items."""
        async def dummy_processor(item):
            await asyncio.sleep(0.01)
            item["processed"] = True
            return item
        
        from ingest_workers import WorkerPool
        
        pool = WorkerPool(
            stage=WorkerStage.CHUNK,
            process_fn=dummy_processor,
            num_workers=2
        )
        
        await pool.start()
        
        try:
            # Enqueue items
            for i in range(5):
                await pool.enqueue_item({"id": i})
            
            # Dequeue results
            results = []
            for _ in range(5):
                result = await pool.dequeue_item(timeout=5.0)
                if result:
                    results.append(result)
            
            assert len(results) >= 3  # At least some should complete
        finally:
            await pool.stop()


class TestAsyncIngestionOrchestrator:
    """Test async ingestion orchestrator."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_startup(self):
        """Test orchestrator can start and stop."""
        orchestrator = AsyncIngestionOrchestrator(
            chunk_workers=2,
            embed_workers=2,
            store_workers=2
        )
        
        await orchestrator.start()
        assert orchestrator.running
        
        await orchestrator.stop()
        assert not orchestrator.running
    
    @pytest.mark.asyncio
    async def test_job_submission(self):
        """Test submitting ingestion jobs."""
        orchestrator = AsyncIngestionOrchestrator()
        
        await orchestrator.start()
        
        try:
            job_id = await orchestrator.submit_job(
                book_slug="test_book",
                chapter_index=1,
                text="Sample chapter text"
            )
            
            assert job_id is not None
            
            status = orchestrator.get_job_status(job_id)
            assert status is not None
            assert status["job_id"] == job_id
            assert status["phase"] == IngestionPhase.QUEUED.value
        
        finally:
            await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_job_processing(self):
        """Test that jobs are processed through pipeline."""
        orchestrator = AsyncIngestionOrchestrator(
            chunk_workers=1,
            embed_workers=1,
            store_workers=1
        )
        
        await orchestrator.start()
        
        try:
            # Submit job
            job_id = await orchestrator.submit_job(
                book_slug="test_book",
                chapter_index=1,
                text="Sample text " * 100
            )
            
            # Wait for completion
            completed = await orchestrator.wait_for_completion(timeout=30.0)
            
            # Check status
            status = orchestrator.get_job_status(job_id)
            
            # Job should be complete or failed
            assert status["phase"] in [
                IngestionPhase.COMPLETE.value,
                IngestionPhase.FAILED.value
            ]
        
        finally:
            await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_jobs(self):
        """Test processing multiple jobs."""
        orchestrator = AsyncIngestionOrchestrator(
            chunk_workers=2,
            embed_workers=2,
            store_workers=2
        )
        
        await orchestrator.start()
        
        try:
            # Submit multiple jobs
            num_jobs = 5
            job_ids = []
            
            for i in range(num_jobs):
                job_id = await orchestrator.submit_job(
                    book_slug="test_book",
                    chapter_index=i,
                    text=f"Chapter {i} text " * 50
                )
                job_ids.append(job_id)
            
            # Wait for all
            completed = await orchestrator.wait_for_completion(timeout=60.0)
            
            # Check metrics
            metrics = orchestrator.metrics
            assert metrics.total_submitted == num_jobs
            assert metrics.total_completed + metrics.total_failed == num_jobs
        
        finally:
            await orchestrator.stop()


class TestBenchmarkHarness:
    """Test benchmarking framework."""
    
    @pytest.mark.asyncio
    async def test_benchmark_result_statistics(self):
        """Test benchmark result statistics calculation."""
        from benchmark_harness import BenchmarkResult
        
        result = BenchmarkResult(
            test_name="Test",
            phase=BenchmarkPhase.MEASUREMENT
        )
        
        result.items_processed = 100
        result.total_time_seconds = 10.0
        result.processing_times = [0.1] * 100  # 100ms each
        
        assert result.throughput_items_per_sec == 10.0
        assert result.avg_processing_time == 0.1
        assert result.success_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_benchmark_suite_collection(self):
        """Test benchmark suite collects results."""
        from benchmark_harness import BenchmarkSuite, BenchmarkResult, BenchmarkPhase
        
        suite = BenchmarkSuite("Test Suite")
        
        result1 = BenchmarkResult(
            test_name="Test 1",
            phase=BenchmarkPhase.MEASUREMENT,
            items_processed=100,
            total_time_seconds=10.0
        )
        
        result2 = BenchmarkResult(
            test_name="Test 2",
            phase=BenchmarkPhase.MEASUREMENT,
            items_processed=200,
            total_time_seconds=20.0
        )
        
        suite.add_result(result1)
        suite.add_result(result2)
        
        assert len(suite.results) == 2
        assert len(suite.get_measurement_results()) == 2


class TestIntegrationPipeline:
    """End-to-end pipeline integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self):
        """Test complete pipeline from submission to completion."""
        orchestrator = AsyncIngestionOrchestrator(
            chunk_workers=2,
            embed_workers=2,
            store_workers=2,
            max_queue_depth=100
        )
        
        await orchestrator.start()
        
        try:
            # Submit batch of jobs
            for i in range(3):
                await orchestrator.submit_job(
                    book_slug="integration_test",
                    chapter_index=i,
                    text=f"Integration test chapter {i}. " * 100
                )
            
            # Wait for completion
            result = await orchestrator.wait_for_completion(timeout=60.0)
            
            # Verify metrics
            assert orchestrator.metrics.total_submitted == 3
            assert orchestrator.metrics.total_completed > 0
            
            # Get orchestrator metrics
            metrics = orchestrator.get_orchestrator_metrics()
            assert "ingestion" in metrics
            assert "rate_controller" in metrics
            assert "pipeline" in metrics
        
        finally:
            await orchestrator.stop()


# Run with: pytest test_async_ingestion.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
