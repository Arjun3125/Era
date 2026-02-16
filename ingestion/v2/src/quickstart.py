#!/usr/bin/env python3
"""
Quick Start Example: Production Async Ingestion Pipeline

This script demonstrates:
1. Creating an async ingestion orchestrator
2. Submitting ingestion jobs
3. Processing through the pipeline
4. Running benchmarks
5. Collecting metrics
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from async_ingestion_orchestrator import AsyncIngestionOrchestrator
from benchmark_harness import BenchmarkHarness, BenchmarkPhase
from ingestion_config import create_orchestrator_config


async def example_basic_ingestion():
    """Example 1: Basic ingestion without benchmarking."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Ingestion")
    print("="*70)
    
    # Create orchestrator with standard config
    config = create_orchestrator_config(environment="standard")
    orchestrator = AsyncIngestionOrchestrator(**config)
    
    await orchestrator.start()
    
    try:
        # Submit some test chapters
        print("\nSubmitting 5 test chapters...")
        job_ids = []
        
        for i in range(5):
            text = f"This is chapter {i} of our test book. " * 50  # 50 repetitions
            job_id = await orchestrator.submit_job(
                book_slug="test-book",
                chapter_index=i,
                text=text,
                priority=i % 3
            )
            job_ids.append(job_id)
            print(f"  Submitted chapter {i}: {job_id}")
        
        # Wait for completion
        print("\nWaiting for all chapters to process...")
        completed = await orchestrator.wait_for_completion(timeout=60.0)
        
        if not completed:
            print("[WARN] Timeout - some items may still be processing")
        else:
            print("[OK] All chapters processed!")
        
        # Show results
        print("\nResults:")
        all_jobs = orchestrator.get_all_jobs()
        for job in all_jobs:
            status = "[OK]" if job["phase"] == "complete" else "[FAIL]"
            print(f"  {status} {job['job_id'][:8]}... | {job['phase']}")
        
        # Show metrics
        metrics = orchestrator.get_orchestrator_metrics()
        print("\nMetrics:")
        ingest_metrics = metrics["ingestion"]
        print(f"  Total submitted: {ingest_metrics['total_submitted']}")
        print(f"  Total completed: {ingest_metrics['total_completed']}")
        print(f"  Total failed: {ingest_metrics['total_failed']}")
        print(f"  Throughput: {ingest_metrics['throughput_items_per_sec']:.2f} items/sec")
        print(f"  Success rate: {ingest_metrics['success_rate_percent']:.1f}%")
        
    finally:
        await orchestrator.stop()


async def example_with_benchmarks():
    """Example 2: Benchmarking the pipeline."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Pipeline Benchmarking")
    print("="*70)
    
    # Use aggressive config for faster testing
    config = create_orchestrator_config(environment="high_throughput")
    # config already has only the parameters AsyncIngestionOrchestrator accepts
    orchestrator = AsyncIngestionOrchestrator(**config)
    
    await orchestrator.start()
    
    try:
        harness = BenchmarkHarness(orchestrator)
        
        # Warmup run
        print("\nPhase 1: Warmup")
        await harness.run_test(
            test_name="Warmup (10 items)",
            num_items=10,
            phase=BenchmarkPhase.WARMUP,
            item_size=500,
            wait_timeout=30.0
        )
        
        # Scaling test with different item counts
        print("\n\nPhase 2: Scaling Tests")
        await harness.run_scaling_benchmark(
            item_counts=[50, 100, 200],
            item_size=1000
        )
        
        # Print summary
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        harness.print_summary()
        
        # Save results
        results_file = "benchmark_results_quickstart.json"
        harness.save_results(results_file)
        print(f"\n[OK] Results saved to {results_file}")
        
    finally:
        await orchestrator.stop()


async def example_custom_configuration():
    """Example 3: Custom configuration."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Custom Configuration")
    print("="*70)
    
    from adaptive_controller import AdaptiveConfig, RateLimit
    from distributed_queue import InMemoryQueue
    
    # Create custom rate limiting (very conservative)
    custom_rate = RateLimit(
        tokens_per_second=5.0,  # Very slow
        max_burst=20.0,
        refill_interval=0.1
    )
    
    custom_adaptive = AdaptiveConfig(
        base_rate_limit=custom_rate,
        congestion_threshold=0.6,
        recovery_threshold=0.2,
        backpressure_factor=0.3,
        recovery_factor=1.1
    )
    
    # Create custom queue
    queue = InMemoryQueue(max_size=50)
    
    # Create orchestrator with custom config
    orchestrator = AsyncIngestionOrchestrator(
        queue=queue,
        adaptive_config=custom_adaptive,
        chunk_workers=1,  # Single worker for simplicity
        embed_workers=1,
        store_workers=1,
        max_queue_depth=50
    )
    
    await orchestrator.start()
    
    try:
        print("\nCustom Configuration:")
        print(f"  Rate limit: 5 tokens/sec (very conservative)")
        print(f"  Queue size: 50 max")
        print(f"  Workers: 1 per stage")
        
        # Submit items and observe rate limiting
        print("\nSubmitting 5 items (watch rate limiting in action)...")
        
        for i in range(5):
            job_id = await orchestrator.submit_job(
                book_slug="custom-config-test",
                chapter_index=i,
                text=f"Chapter {i} " * 100,
                priority=5 - i  # Higher priority for first items
            )
            print(f"  Submitted item {i} at {asyncio.get_event_loop().time():.2f}s")
        
        # Wait a bit to see processing
        await asyncio.sleep(5)
        
        # Show rate controller state
        controller_metrics = orchestrator.controller.get_metrics()
        print(f"\nRate Controller State:")
        print(f"  Current rate multiplier: {controller_metrics['current_rate_multiplier']}")
        print(f"  Tokens available: {controller_metrics['tokens_available']:.1f}")
        print(f"  Queue depth: {controller_metrics['queue_depth']}")
        
    finally:
        await orchestrator.stop()


async def example_error_handling():
    """Example 4: Error handling and retries."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Error Handling and Retries")
    print("="*70)
    
    config = create_orchestrator_config(environment="standard")
    orchestrator = AsyncIngestionOrchestrator(**config)
    
    await orchestrator.start()
    
    try:
        # Submit jobs with various characteristics
        print("\nSubmitting test jobs with edge cases:")
        
        # Normal job
        job1 = await orchestrator.submit_job(
            book_slug="test",
            chapter_index=1,
            text="Normal chapter content " * 100
        )
        print(f"  Job 1 (Normal): {job1}")
        
        # Empty content job (may stress the system)
        job2 = await orchestrator.submit_job(
            book_slug="test",
            chapter_index=2,
            text=""
        )
        print(f"  Job 2 (Empty): {job2}")
        
        # Very large job
        job3 = await orchestrator.submit_job(
            book_slug="test",
            chapter_index=3,
            text="Large chapter " * 10000
        )
        print(f"  Job 3 (Large): {job3}")
        
        # Wait for processing
        print("\nWaiting for processing...")
        await orchestrator.wait_for_completion(timeout=60.0)
        
        # Check status of each job
        print("\nJob Status After Processing:")
        for i, job_id in enumerate([job1, job2, job3], 1):
            status = orchestrator.get_job_status(job_id)
            phase = status["phase"]
            error = status.get("error", "")
            
            if phase == "complete":
                print(f"  Job {i}: [OK] Complete")
            elif phase == "failed":
                print(f"  Job {i}: [FAIL] Failed - {error}")
            else:
                print(f"  Job {i}: [...] {phase}")
        
    finally:
        await orchestrator.stop()


async def main():
    """Run all examples."""
    print("\n" + "#"*70)
    print("# ERA Production Async Ingestion Pipeline - Quick Start")
    print("#"*70)
    
    if len(sys.argv) > 1:
        # Run specific example
        example_num = sys.argv[1]
        examples = {
            "1": example_basic_ingestion,
            "2": example_with_benchmarks,
            "3": example_custom_configuration,
            "4": example_error_handling,
        }
        
        if example_num in examples:
            await examples[example_num]()
        else:
            print(f"Unknown example: {example_num}")
            print("Usage: python quickstart.py [1|2|3|4]")
    else:
        # Run all examples
        await example_basic_ingestion()
        await example_with_benchmarks()
        await example_custom_configuration()
        await example_error_handling()
    
    print("\n" + "="*70)
    print("[OK] Quick start examples completed!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review README_PRODUCTION_PIPELINE.md for detailed documentation")
    print("  2. Integrate real worker functions (chunking, embedding, storage)")
    print("  3. Configure for your database and embedding service")
    print("  4. Deploy to production (Docker/Kubernetes)")
    print("  5. Monitor with Prometheus metrics")
    print("\nDocumentation:")
    print("  - Adaptive Controller: For rate limiting and backpressure")
    print("  - Distributed Queue: For reliable job queueing")
    print("  - Ingestion Config: For environment presets")
    print("  - Benchmark Harness: For performance testing")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
