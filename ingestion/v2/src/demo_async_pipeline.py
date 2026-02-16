"""Demo/test runner for async ingestion pipeline."""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, r'c:\era\ingestion\v2\src')

from async_ingest_config import Chunk
from async_ingest_orchestrator import AsyncIngestionPipeline


def stub_parse_func(path: str):
    """Stub parser that generates synthetic chunks (must be defined at module level for multiprocessing)."""
    print(f"[StubParser] Parsing {path}...")
    chunks = []
    for i in range(10):
        chunk = Chunk(
            text=f"This is chunk {i} from {path}. " * 20,
            domain=["base", "strategy", "conflict"][i % 3],
            category=["principles", "rules", "claims"][i % 3],
            metadata={"index": i, "source": path},
            source_book=path,
            source_chapter=i,
        )
        chunks.append(chunk)
    return chunks


async def main():
    print("=" * 70)
    print("ASYNC INGESTION PIPELINE - INTEGRATION TEST")
    print("=" * 70 + "\n")
    
    pipeline = AsyncIngestionPipeline(output_root="data/test_ministers")
    
    try:
        print("[Pipeline] Starting ingestion with 2 books, 2 embed workers...\n")
        
        metrics = await pipeline.run(
            book_paths=["book1.json", "book2.json"],
            parse_func=stub_parse_func,
            num_embed_workers=2,
        )
        
        print("\n" + "=" * 70)
        print("PIPELINE RESULTS")
        print("=" * 70)
        print(f"Total processed: {metrics['processed_chunks']} chunks")
        print(f"Throughput: {metrics['throughput_chunks_per_sec']:.2f} chunks/sec")
        print(f"Avg embed latency: {metrics['avg_embed_latency_ms']:.2f} ms")
        print(f"Avg DB latency: {metrics['avg_db_latency_ms']:.2f} ms")
        print(f"Rate limit hits: {metrics['rate_limit_hits']}")
        print(f"Errors: {metrics['errors']}")
        print("=" * 70 + "\n")
        
        if metrics['processed_chunks'] > 0:
            print("OK: INTEGRATION TEST PASSED")
            return True
        else:
            print("FAIL: No chunks were processed")
            return False
            
    except Exception as e:
        print(f"\nFAIL: Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
