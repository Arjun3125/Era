"""Production Benchmarking Framework for Ingestion Pipeline"""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import statistics


class BenchmarkPhase(Enum):
    """Benchmark test phases."""
    WARMUP = "warmup"
    MEASUREMENT = "measurement"
    COOLDOWN = "cooldown"


@dataclass
class BenchmarkResult:
    """Single benchmark test result."""
    test_name: str
    phase: BenchmarkPhase
    items_processed: int = 0
    items_failed: int = 0
    total_time_seconds: float = 0.0
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    processing_times: List[float] = field(default_factory=list)
    notes: str = ""
    
    @property
    def throughput_items_per_sec(self) -> float:
        """Calculate items per second."""
        if self.total_time_seconds > 0:
            return self.items_processed / self.total_time_seconds
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.items_processed + self.items_failed
        if total > 0:
            return (self.items_processed / total) * 100
        return 0.0
    
    @property
    def avg_processing_time(self) -> float:
        """Average processing time per item."""
        if self.processing_times:
            return statistics.mean(self.processing_times)
        return 0.0
    
    @property
    def median_processing_time(self) -> float:
        """Median processing time."""
        if self.processing_times:
            return statistics.median(self.processing_times)
        return 0.0
    
    @property
    def p95_processing_time(self) -> float:
        """95th percentile processing time."""
        if len(self.processing_times) > 0:
            return statistics.quantiles(self.processing_times, n=20)[18]  # 95th percentile
        return 0.0
    
    @property
    def p99_processing_time(self) -> float:
        """99th percentile processing time."""
        if len(self.processing_times) > 1:
            return statistics.quantiles(self.processing_times, n=100)[98]  # 99th percentile
        return 0.0
    
    @property
    def max_processing_time(self) -> float:
        """Maximum processing time."""
        return max(self.processing_times) if self.processing_times else 0.0
    
    @property
    def min_processing_time(self) -> float:
        """Minimum processing time."""
        return min(self.processing_times) if self.processing_times else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "phase": self.phase.value,
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "total_time_seconds": round(self.total_time_seconds, 3),
            "throughput_items_per_sec": round(self.throughput_items_per_sec, 2),
            "success_rate_percent": round(self.success_rate, 2),
            "processing_time_ms": {
                "avg": round(self.avg_processing_time * 1000, 2),
                "median": round(self.median_processing_time * 1000, 2),
                "p95": round(self.p95_processing_time * 1000, 2),
                "p99": round(self.p99_processing_time * 1000, 2),
                "min": round(self.min_processing_time * 1000, 2),
                "max": round(self.max_processing_time * 1000, 2)
            },
            "notes": self.notes
        }


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    results: List[BenchmarkResult] = field(default_factory=list)
    
    def add_result(self, result: BenchmarkResult):
        """Add a result to the suite."""
        self.results.append(result)
    
    def get_results_by_phase(self, phase: BenchmarkPhase) -> List[BenchmarkResult]:
        """Get results for a specific phase."""
        return [r for r in self.results if r.phase == phase]
    
    def get_measurement_results(self) -> List[BenchmarkResult]:
        """Get measurement phase results (primary results)."""
        return self.get_results_by_phase(BenchmarkPhase.MEASUREMENT)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "total_tests": len(self.results),
            "results": [r.to_dict() for r in self.results]
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def save(self, filepath: str):
        """Save results to JSON file."""
        with open(filepath, "w") as f:
            f.write(self.to_json())
        print(f"Benchmark results saved to {filepath}")


class BenchmarkHarness:
    """Framework for running benchmark tests."""
    
    def __init__(self, orchestrator):
        """
        Initialize harness.
        
        Args:
            orchestrator: AsyncIngestionOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.suite = BenchmarkSuite("Ingestion Pipeline Benchmarks")
    
    async def run_test(
        self,
        test_name: str,
        num_items: int,
        phase: BenchmarkPhase = BenchmarkPhase.MEASUREMENT,
        book_slug: str = "benchmark_book",
        item_size: int = 1000,  # characters
        wait_timeout: float = 300.0
    ) -> BenchmarkResult:
        """
        Run a single benchmark test.
        
        Args:
            test_name: Name of the test
            num_items: Number of items to process
            phase: Benchmark phase
            book_slug: Book slug for test data
            item_size: Size of each test item (characters)
            wait_timeout: Timeout for completion
            
        Returns:
            BenchmarkResult
        """
        result = BenchmarkResult(test_name=test_name, phase=phase)
        result.start_time = datetime.utcnow()
        
        print(f"\n{'='*60}")
        print(f"Benchmark: {test_name} ({phase.value.upper()})")
        print(f"Items: {num_items}, Item size: {item_size} chars")
        print(f"{'='*60}")
        
        # Reset orchestrator metrics
        self.orchestrator.metrics = self.orchestrator.metrics.__class__()
        
        # Submit items
        print("Submitting items...")
        start_submit = time.time()
        
        for i in range(num_items):
            text = "sample text " * (item_size // 12)
            await self.orchestrator.submit_job(
                book_slug=book_slug,
                chapter_index=i,
                text=text,
                priority=num_items - i  # Higher priority for later items
            )
            
            if (i + 1) % max(1, num_items // 10) == 0:
                print(f"  Submitted {i + 1}/{num_items} items")
        
        submit_time = time.time() - start_submit
        print(f"Submit complete in {submit_time:.2f}s")
        
        # Wait for completion
        print("Processing items...")
        start_process = time.time()
        
        completed = await self.orchestrator.wait_for_completion(timeout=wait_timeout)
        
        if not completed:
            print(f"WARNING: Timeout after {wait_timeout}s")
            result.notes = f"Timeout (partial results) - completed {self.orchestrator.metrics.total_completed}/{num_items}"
        
        process_time = time.time() - start_process
        
        # Collect results
        result.items_processed = self.orchestrator.metrics.total_completed
        result.items_failed = self.orchestrator.metrics.total_failed
        result.total_time_seconds = process_time
        
        # Estimate processing times from pipeline metrics
        pipeline_metrics = self.orchestrator.pipeline.get_all_metrics()
        for stage_workers in pipeline_metrics.values():
            for worker_metrics in stage_workers:
                for _ in range(worker_metrics["items_processed"]):
                    result.processing_times.append(
                        worker_metrics["avg_time_per_item_ms"] / 1000.0
                    )
        
        # If no detailed metrics, estimate from total
        if not result.processing_times and result.items_processed > 0:
            avg_time = process_time / result.items_processed
            result.processing_times = [avg_time] * result.items_processed
        
        result.end_time = datetime.utcnow()
        
        # Print summary
        print(f"\nResults:")
        print(f"  Items processed: {result.items_processed}/{num_items}")
        print(f"  Items failed: {result.items_failed}")
        print(f"  Success rate: {result.success_rate:.1f}%")
        print(f"  Processing time: {process_time:.2f}s")
        print(f"  Throughput: {result.throughput_items_per_sec:.2f} items/sec")
        print(f"  Avg latency: {result.avg_processing_time*1000:.2f}ms")
        print(f"  P95 latency: {result.p95_processing_time*1000:.2f}ms")
        print(f"  P99 latency: {result.p99_processing_time*1000:.2f}ms")
        
        self.suite.add_result(result)
        return result
    
    async def run_scaling_benchmark(
        self,
        item_counts: List[int] = [100, 500, 1000],
        item_size: int = 1000
    ):
        """
        Run benchmark with increasing item counts to test scaling.
        
        Args:
            item_counts: List of item counts to test
            item_size: Size of each test item
        """
        print(f"\n{'#'*60}")
        print(f"SCALING BENCHMARK")
        print(f"{'#'*60}")
        
        for count in item_counts:
            await self.run_test(
                test_name=f"Scaling Test - {count} items",
                num_items=count,
                phase=BenchmarkPhase.MEASUREMENT,
                item_size=item_size
            )
    
    async def run_load_profile_benchmark(
        self,
        duration_seconds: float = 60,
        target_throughput: float = 10  # items/sec
    ):
        """
        Run benchmark simulating steady load profile.
        
        Args:
            duration_seconds: How long to run
            target_throughput: Target items per second
        """
        print(f"\n{'#'*60}")
        print(f"LOAD PROFILE BENCHMARK - {duration_seconds}s at {target_throughput} items/sec")
        print(f"{'#'*60}")
        
        result = BenchmarkResult(
            test_name=f"Load Profile - {target_throughput} items/sec",
            phase=BenchmarkPhase.MEASUREMENT
        )
        result.start_time = datetime.utcnow()
        
        interval = 1.0 / target_throughput
        end_time = time.time() + duration_seconds
        item_count = 0
        
        print("Submitting items at target throughput...")
        while time.time() < end_time:
            await self.orchestrator.submit_job(
                book_slug="load_test",
                chapter_index=item_count,
                text="sample text " * 100,
                priority=0
            )
            item_count += 1
            await asyncio.sleep(interval)
        
        print(f"Submitted {item_count} items, waiting for processing...")
        
        # Wait for remaining items
        max_wait = duration_seconds * 2
        await asyncio.wait_for(
            self.orchestrator.wait_for_completion(),
            timeout=max_wait
        )
        
        result.items_processed = self.orchestrator.metrics.total_completed
        result.items_failed = self.orchestrator.metrics.total_failed
        result.total_time_seconds = time.time() - result.start_time.timestamp()
        result.end_time = datetime.utcnow()
        
        print(f"\nLoad Profile Results:")
        print(f"  Items submitted: {item_count}")
        print(f"  Items completed: {result.items_processed}")
        print(f"  Items failed: {result.items_failed}")
        print(f"  Actual throughput: {result.throughput_items_per_sec:.2f} items/sec")
        
        self.suite.add_result(result)
    
    def print_summary(self):
        """Print summary of all results."""
        print(f"\n{'='*60}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'='*60}")
        
        measurement_results = self.suite.get_measurement_results()
        
        for result in measurement_results:
            print(f"\n{result.test_name}:")
            print(f"  Throughput: {result.throughput_items_per_sec:.2f} items/sec")
            print(f"  Latency (avg/p95/p99): {result.avg_processing_time*1000:.1f}ms / {result.p95_processing_time*1000:.1f}ms / {result.p99_processing_time*1000:.1f}ms")
            print(f"  Success: {result.success_rate:.1f}%")
    
    def save_results(self, filepath: str):
        """Save results to file."""
        self.suite.save(filepath)


# Example usage
async def example_benchmarks():
    """Example: Running benchmarks."""
    from async_ingestion_orchestrator import AsyncIngestionOrchestrator
    
    orchestrator = AsyncIngestionOrchestrator(
        chunk_workers=2,
        embed_workers=2,
        store_workers=2
    )
    
    await orchestrator.start()
    
    try:
        harness = BenchmarkHarness(orchestrator)
        
        # Run warmup
        await harness.run_test(
            test_name="Warmup Run",
            num_items=10,
            phase=BenchmarkPhase.WARMUP,
            item_size=500
        )
        
        # Run scaling tests
        await harness.run_scaling_benchmark(
            item_counts=[50, 100, 200],
            item_size=1000
        )
        
        # Print summary
        harness.print_summary()
        
        # Save results
        harness.save_results("benchmark_results.json")
    
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    # Note: This example requires AsyncIngestionOrchestrator
    # asyncio.run(example_benchmarks())
    
    # Instead, show the data structure
    print("Benchmark Framework Available")
    print("- BenchmarkResult: Single test result with statistics")
    print("- BenchmarkSuite: Collection of results")
    print("- BenchmarkHarness: Framework for running tests")
    print("\nRun with an orchestrator instance to execute benchmarks")
