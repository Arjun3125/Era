"""Quick test of async embedding with detailed logging."""
import asyncio
import json
import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

sys.path.insert(0, r'c:\era')

from ingestion.v2.src.async_ingest_orchestrator import AsyncIngestionPipeline
from ingestion.v2.src.ollama_client import OllamaClient
from ingestion.v2.src.config import DEFAULT_EMBED_MODEL
from ingestion.v2.src.async_ingest_config import Chunk

# Create a test with just 1 chunk
test_nodes = [
    {"text": "The principles of wealth.", "domain": "strategy", "category": "principles", "source_book": "TEST", "source_chapter": "ch1"},
]

test_file = "test_single.json"
with open(test_file, 'w') as f:
    json.dump(test_nodes, f)

def _parse_chunks_from_file(path: str):
    """Load test chunks."""
    print(f"[PARSER] Starting to parse {path}")
    chunks = []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        print(f"[PARSER] Loaded {len(data)} items from file")
        for item in data:
            c = Chunk(
                text=item.get('text', ''),
                domain=item.get('domain', 'base'),
                category=item.get('category', 'content'),
                source_book=item.get('source_book'),
                source_chapter=item.get('source_chapter'),
            )
            chunks.append(c)
        print(f"[PARSER] Created {len(chunks)} Chunk objects")
    except Exception as e:
        print(f"[PARSER] Error loading chunks: {e}")
    return chunks

async def test_async_embed():
    """Test async pipeline with ThreadPoolExecutor."""
    print("=" * 70)
    print("ASYNC EMBEDDING TEST - Single Chunk")
    print("=" * 70 + "\n")
    
    embed_client = OllamaClient(model=DEFAULT_EMBED_MODEL)
    pipeline = AsyncIngestionPipeline(db_dsn=None, output_root="test_ministers_single", llm_client=embed_client)
    
    try:
        print(f"[MAIN] Testing with embed model: {DEFAULT_EMBED_MODEL}")
        print(f"[MAIN] Input: {test_file} with {len(test_nodes)} chunks\n")
        
        metrics = await asyncio.wait_for(
            pipeline.run(
                book_paths=[test_file],
                parse_func=_parse_chunks_from_file,
                num_embed_workers=1,
            ),
            timeout=60.0
        )
        
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Processed chunks: {metrics.get('processed_chunks', 0)}")
        print(f"Throughput: {metrics.get('throughput_chunks_per_sec', 0):.2f} chunks/sec")
        print(f"Errors: {metrics.get('errors', 0)}")
        
        if metrics.get('processed_chunks', 0) > 0:
            print("\n✓ TEST PASSED - Embedding is working!")
            return True
        else:
            print("\n✗ TEST FAILED - No chunks processed")
            return False
            
    except asyncio.TimeoutError:
        print(f"\n✗ TEST TIMEOUT - Pipeline exceeded 60 seconds")
        return False
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        result = asyncio.run(test_async_embed())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n[MAIN] Test interrupted")
        sys.exit(1)
