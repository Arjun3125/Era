"""Test suite for async ingestion pipeline."""
import asyncio
import json
import logging
import sys
sys.path.insert(0, r'c:\era\ingestion\v2\src')

from async_ingest_config import Chunk
from async_ingest_orchestrator import AsyncIngestionPipeline
from ingest_metrics import IngestMetrics


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def stub_parse_func(path: str) -> list:
    """Stub parser that generates synthetic chunks."""
    print(f"[StubParser] Parsing {path}...")
    
    chunks = []
    for i in range(10):  # 10 chunks per "book"
        chunk = Chunk(
            text=f"This is chunk {i} from {path}. " * 20,  # Some text
            domain=["base", "strategy", "conflict"][i % 3],
            category=["principles", "rules", "claims"][i % 3],
            metadata={"index": i, "source": path},
            source_book=path,
            source_chapter=i,
        )
        chunks.append(chunk)
    
    return chunks


async def test_simple_pipeline():
    """Test the async pipeline with stub data."""
    print("\n" + "=" * 70)
    print("TEST 1: Simple Pipeline with Stub Data")
    print("=" * 70 + "\n")
    
    pipeline = AsyncIngestionPipeline(output_root="data/test_ministers")
    
    # Run pipeline with stub books
    metrics = await pipeline.run(
        book_paths=["book1.json", "book2.json"],
        parse_func=stub_parse_func,
        num_embed_workers=2,
    )
    
    print(f"\nTest 1 Results:")
    print(f"  Total processed: {metrics['processed_chunks']}")
    print(f"  Throughput: {metrics['throughput_chunks_per_sec']:.2f} chunks/sec")
    print(f"  Avg embed latency: {metrics['avg_embed_latency_ms']:.2f}ms")
    
    assert metrics['processed_chunks'] > 0, "Pipeline should process chunks"
    print("✓ Test 1 PASSED\n")


async def test_metrics_collection():
    """Test metrics collection and reporting."""
    print("=" * 70)
    print("TEST 2: Metrics Collection")
    print("=" * 70 + "\n")
    
    metrics = IngestMetrics()
    
    # Simulate some operations
    metrics.record_embed(0.5)
    metrics.record_embed(0.6)
    metrics.record_db(0.1)
    metrics.record_db(0.12)
    metrics.record_processed(100)
    metrics.record_processed(50)
    
    report = metrics.report()
    
    print(f"Metrics Report:")
    print(f"  Processed: {report['processed_chunks']}")
    print(f"  Avg embed latency: {report['avg_embed_latency_ms']:.2f}ms")
    print(f"  Avg DB latency: {report['avg_db_latency_ms']:.2f}ms")
    
    assert report['processed_chunks'] == 150
    assert report['avg_embed_latency_ms'] > 0
    print("✓ Test 2 PASSED\n")


async def test_rate_controller():
    """Test adaptive rate controller."""
    print("=" * 70)
    print("TEST 3: Adaptive Rate Controller")
    print("=" * 70 + "\n")
    
    from rate_controller import AdaptiveRateController
    
    controller = AdaptiveRateController(initial_concurrency=5, min_concurrency=2, max_concurrency=20)
    
    # Simulate low latency -> increase concurrency
    for _ in range(20):
        controller.record_success(0.4)
    
    initial = controller.concurrency
    controller.adjust()
    after_low_latency = controller.concurrency
    
    print(f"After low latency (0.4s):")
    print(f"  Concurrency: {initial} → {after_low_latency}")
    assert after_low_latency > initial, "Should increase on low latency"
    
    # Simulate rate limits -> decrease concurrency
    controller.rate_limit_hits = 5
    before = controller.concurrency
    controller.adjust()
    after = controller.concurrency
    
    print(f"After rate limits:")
    print(f"  Concurrency: {before} → {after}")
    assert after < before, "Should decrease on rate limits"
    
    print("✓ Test 3 PASSED\n")


async def test_chunk_dataclass():
    """Test Chunk data model."""
    print("=" * 70)
    print("TEST 4: Chunk Data Model")
    print("=" * 70 + "\n")
    
    chunk = Chunk(
        text="Test chunk text",
        domain="strategy",
        category="principles",
        embedding=[0.1] * 1536,
        source_book="test_book.json",
        source_chapter=5,
    )
    
    db_tuple = chunk.to_db_tuple()
    
    print(f"Chunk ID: {chunk.id}")
    print(f"Domain: {chunk.domain}")
    print(f"Category: {chunk.category}")
    print(f"Embedding dim: {len(chunk.embedding)}")
    print(f"DB tuple length: {len(db_tuple)}")
    
    assert chunk.domain == "strategy"
    assert len(db_tuple) == 8
    print("✓ Test 4 PASSED\n")


def test_imports():
    """Test that all modules can be imported."""
    print("=" * 70)
    print("TEST 5: Import Validation")
    print("=" * 70 + "\n")
    
    try:
        import async_ingest_config
        import rate_controller
        import ingest_metrics
        import async_workers
        import async_ingest_orchestrator
        print("✓ All modules imported successfully")
        print("✓ Test 5 PASSED\n")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("ASYNC INGESTION PIPELINE - TEST SUITE")
    print("=" * 70)
    
    # Import tests (synchronous)
    if not test_imports():
        return False
    
    # Async tests
    try:
        await test_metrics_collection()
        await test_rate_controller()
        await test_chunk_dataclass()
        await test_simple_pipeline()
        
        print("=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
