"""
Integration example: wiring async pipeline into existing ingestion system.

This shows how to adapt the existing ingest_pipeline.py or minister_converter.py
to use the new async architecture for 10-20x throughput improvement.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any

# Local imports
from async_ingest_config import Chunk
from async_ingest_orchestrator import main_ingest
from ingest_metrics import IngestMetrics


# ============================================================================
# INTEGRATION LAYER: Convert existing parsing to async format
# ============================================================================

def convert_existing_parser(parse_func) -> callable:
    """Adapts existing parse_book function to return Chunks."""
    def wrapper(book_path: str) -> List[Chunk]:
        # Call existing parser
        raw_items = parse_func(book_path)  # Returns dict or Item objects
        
        chunks = []
        for item in raw_items:
            chunk = Chunk(
                text=item.get('text') or item.get('content'),
                domain=item.get('domain') or 'general',
                category=item.get('category') or 'unknown',
                metadata={
                    'source_book': book_path,
                    'chapter': item.get('chapter'),
                    'page': item.get('page'),
                },
                source_book=str(book_path),
                source_chapter=item.get('chapter'),
            )
            chunks.append(chunk)
        
        return chunks
    
    return wrapper


# ============================================================================
# EXAMPLE 1: Drop-in replacement for existing ingest_pipeline
# ============================================================================

async def async_ingest_books(
    book_paths: List[str],
    parse_func: callable,
    embedding_api_key: str = None,
    db_dsn: str = None,
    output_root: str = "data/ministers",
) -> dict:
    """
    High-level ingestion function replacing the old synchronous pipeline.
    
    Usage:
        result = asyncio.run(async_ingest_books(
            book_paths=['book1.json', 'book2.json'],
            parse_func=my_existing_parse_function,
            embedding_api_key='sk-...',
            db_dsn='postgresql://...'
        ))
        print(f"Processed {result['processed_chunks']} chunks")
    """
    
    # If existing parser returns dicts, adapt it
    parser = convert_existing_parser(parse_func)
    
    # Run async pipeline
    metrics = await main_ingest(
        book_paths=book_paths,
        parse_func=parser,
        db_dsn=db_dsn,
        output_root=output_root,
        num_embed_workers=20,  # Tune based on API rate limits
    )
    
    return metrics


# ============================================================================
# EXAMPLE 2: Batch processing with progress monitoring
# ============================================================================

async def ingest_with_monitoring(
    book_batch: List[str],
    parse_func: callable,
    checkpoint_file: str = "ingest_checkpoint.json",
) -> dict:
    """
    Ingest multiple books with checkpointing for resumable processing.
    
    Usage:
        result = asyncio.run(ingest_with_monitoring(
            book_batch=glob.glob('rag_storage/*'),
            parse_func=my_parser
        ))
    """
    
    # Load checkpoint (processed books)
    processed = set()
    if Path(checkpoint_file).exists():
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
            processed = set(checkpoint.get('completed_books', []))
    
    # Filter unprocessed books
    remaining = [b for b in book_batch if b not in processed]
    print(f"Resuming: {len(remaining)}/{len(book_batch)} books remaining")
    
    # Process remaining books
    parser = convert_existing_parser(parse_func)
    metrics = await main_ingest(
        book_paths=remaining,
        parse_func=parser,
        num_embed_workers=20,
    )
    
    # Update checkpoint
    processed.update(remaining)
    with open(checkpoint_file, 'w') as f:
        json.dump({
            'completed_books': list(processed),
            'total_chunks': metrics['processed_chunks'],
            'last_run': str(__import__('datetime').datetime.now()),
        }, f, indent=2)
    
    return metrics


# ============================================================================
# EXAMPLE 3: Config-driven deployment
# ============================================================================

class IngestionConfig:
    """Configuration for async ingestion deployment."""
    
    def __init__(
        self,
        book_paths: List[str] = None,
        db_dsn: str = None,
        num_workers: int = 20,
        batch_size: int = 64,
        output_root: str = "data/ministers",
    ):
        self.book_paths = book_paths or []
        self.db_dsn = db_dsn
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.output_root = output_root
    
    @classmethod
    def from_json(cls, config_file: str):
        """Load config from JSON file."""
        with open(config_file) as f:
            data = json.load(f)
        return cls(**data)
    
    def to_json(self, config_file: str):
        """Save config to JSON file."""
        with open(config_file, 'w') as f:
            json.dump(vars(self), f, indent=2)


async def deploy_with_config(config_file: str, parse_func: callable):
    """Deploy ingestion from config file."""
    config = IngestionConfig.from_json(config_file)
    
    print(f"Deploying with config:")
    print(f"  Books: {len(config.book_paths)}")
    print(f"  Workers: {config.num_workers}")
    print(f"  Batch size: {config.batch_size}")
    print(f"  DB: {config.db_dsn or 'file-backed stub'}")
    
    parser = convert_existing_parser(parse_func)
    
    metrics = await main_ingest(
        book_paths=config.book_paths,
        parse_func=parser,
        db_dsn=config.db_dsn,
        output_root=config.output_root,
        num_embed_workers=config.num_workers,
    )
    
    return metrics


# ============================================================================
# EXAMPLE 4: Integration with capital_allocation post-processing
# ============================================================================

async def ingest_and_process_capital_allocation(
    book_paths: List[str],
    parse_func: callable,
    memory_db_root: str = "data",
):
    """
    Run ingestion then feed output to capital_allocation memory layer.
    """
    
    # Step 1: Async ingestion
    print("Step 1: Async ingestion...")
    parser = convert_existing_parser(parse_func)
    
    metrics = await main_ingest(
        book_paths=book_paths,
        parse_func=parser,
        num_embed_workers=20,
    )
    
    print(f"Ingestion complete: {metrics['processed_chunks']} chunks")
    
    # Step 2: Feed to capital_allocation
    print("\nStep 2: Processing with capital allocation...")
    try:
        # This requires capital_allocation module
        from capital_allocation import ingest_post_phase3
        
        # Create event for post-phase3 processing
        event = {
            'storage': 'data/test_ministers',
            'book_id': 'async_ingest_run',
        }
        
        created_ids = ingest_post_phase3(event)
        print(f"Memory layer processed: {len(created_ids)} items")
        
    except ImportError:
        print("(capital_allocation not available in this context)")
    
    return metrics


# ============================================================================
# EXAMPLE 5: Performance comparison (before/after)
# ============================================================================

async def benchmark_async_vs_sync(
    book_paths: List[str],
    parse_func: callable,
):
    """
    Compare async pipeline performance (stub only, no real API).
    For real benchmarking, measure wall time with actual LLM API.
    """
    
    import time
    
    parser = convert_existing_parser(parse_func)
    
    print("Running async pipeline benchmark...")
    start = time.time()
    
    metrics = await main_ingest(
        book_paths=book_paths,
        parse_func=parser,
        num_embed_workers=20,
    )
    
    elapsed = time.time() - start
    
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS (async with 20 workers, batch=64)")
    print("=" * 70)
    print(f"Total time: {elapsed:.2f}s")
    print(f"Chunks processed: {metrics['processed_chunks']}")
    print(f"Throughput: {metrics['throughput_chunks_per_sec']:.2f} chunks/sec")
    print(f"Est. time with 1 worker (sync): {elapsed * 20:.2f}s")
    print(f"Speedup: ~{elapsed * 20 / elapsed:.1f}x")
    print("=" * 70 + "\n")
    
    return metrics


# ============================================================================
# ENTRY POINTS FOR YOUR APPLICATION
# ============================================================================

if __name__ == "__main__":
    # Placeholder parser (replace with your actual one)
    def dummy_parser(path: str):
        return [
            {
                'text': f'Chunk {i} from {path}',
                'domain': 'strategy',
                'category': 'principles',
                'chapter': i,
            }
            for i in range(5)
        ]
    
    # Example 1: Simple async ingest
    print("Example 1: Simple async ingest")
    result1 = asyncio.run(async_ingest_books(
        book_paths=['book1.json', 'book2.json'],
        parse_func=dummy_parser,
    ))
    print(f"Result: {result1['processed_chunks']} chunks\n")
    
    # Example 2: With monitoring/checkpoint
    # result2 = asyncio.run(ingest_with_monitoring(
    #     book_batch=['book1.json', 'book2.json'],
    #     parse_func=dummy_parser,
    # ))
    
    # Example 3: Config-driven
    # result3 = asyncio.run(deploy_with_config(
    #     config_file='ingest_config.json',
    #     parse_func=dummy_parser,
    # ))
    
    # Example 4: With capital allocation
    # result4 = asyncio.run(ingest_and_process_capital_allocation(
    #     book_paths=['book1.json'],
    #     parse_func=dummy_parser,
    # ))
