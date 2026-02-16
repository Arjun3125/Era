"""Main orchestrator for async multi-stage ingestion pipeline."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Callable, Any
import aiohttp

try:
    import asyncpg
except ImportError:
    asyncpg = None

from .async_ingest_config import (
    MAX_EMBED_CONCURRENCY,
    QUEUE_MAXSIZE,
    DB_POOL_MIN_SIZE,
    DB_POOL_MAX_SIZE,
    Chunk,
)
from .rate_controller import AdaptiveRateController
from .ingest_metrics import IngestMetrics
from .async_workers import (
    reader_worker,
    embed_worker,
    db_bulk_writer,
    minister_aggregator,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AsyncIngestionPipeline:
    """Main orchestrator for the async ingestion pipeline."""
    
    def __init__(
        self,
        db_dsn: Optional[str] = None,
        output_root: str = "data/ministers",
        llm_client: Optional[Any] = None,
    ):
        self.db_dsn = db_dsn
        self.output_root = output_root
        self.llm_client = llm_client
        self.metrics = IngestMetrics()
        self.db_pool = None
        self.rate_controller = AdaptiveRateController()
    
    async def initialize_db(self):
        """Initialize database connection pool if DSN provided."""
        if self.db_dsn and asyncpg:
            try:
                self.db_pool = await asyncpg.create_pool(
                    self.db_dsn,
                    min_size=DB_POOL_MIN_SIZE,
                    max_size=DB_POOL_MAX_SIZE,
                )
                logger.info("[Pipeline] Database pool initialized")
            except Exception as e:
                logger.warning(f"[Pipeline] Could not connect to DB: {e}; using stub storage")
                self.db_pool = None
        else:
            logger.info("[Pipeline] Using file-backed storage (vector_db stub)")
    
    async def close_db(self):
        """Close database connection pool."""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("[Pipeline] Database pool closed")
    
    async def run(
        self,
        book_paths: List[str],
        parse_func: Callable,
        num_embed_workers: int = MAX_EMBED_CONCURRENCY,
    ) -> dict:
        """Run the full async ingestion pipeline.
        
        Args:
            book_paths: List of paths to book files
            parse_func: Function to parse a book file into Chunks
            num_embed_workers: Number of concurrent embedding workers
        
        Returns:
            Dictionary with final metrics
        """
        
        # Initialize DB
        await self.initialize_db()
        
        # Create queues
        chunk_queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        vector_queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        minister_queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        
        # Thread pool for I/O-bound parsing (more reliable on Windows than ProcessPoolExecutor)
        with ThreadPoolExecutor(max_workers=4) as pool:
            async with aiohttp.ClientSession() as session:
                
                # Create producer tasks (readers)
                producers = [
                    asyncio.create_task(
                        reader_worker(path, chunk_queue, pool, parse_func, self.metrics)
                    )
                    for path in book_paths
                ]
                
                # Create embedding worker tasks
                embed_workers = [
                    asyncio.create_task(
                        embed_worker(
                            chunk_queue,
                            vector_queue,
                            session,
                            self.llm_client,  # embed_func / llm client
                            self.rate_controller,
                            self.metrics,
                            worker_id=i,
                        )
                    )
                    for i in range(num_embed_workers)
                ]
                
                # Create DB writer task
                db_writer = asyncio.create_task(
                    db_bulk_writer(
                        vector_queue,
                        minister_queue,
                        self.db_pool,
                        self.metrics,
                    )
                )
                
                # Create minister aggregator task
                minister_task = asyncio.create_task(
                    minister_aggregator(
                        minister_queue,
                        self.metrics,
                        self.output_root,
                    )
                )
                
                # Wait for all readers to finish
                logger.info("[Pipeline] Waiting for readers to complete...")
                await asyncio.gather(*producers)
                logger.info("[Pipeline] All readers finished")
                
                # Wait for chunk queue to drain
                logger.info("[Pipeline] Waiting for chunk queue to drain...")
                await chunk_queue.join()
                logger.info("[Pipeline] Chunk queue drained")
                
                # Signal embed workers to exit
                logger.info("[Pipeline] Signaling embed workers to finish...")
                for _ in range(num_embed_workers):
                    await chunk_queue.put(None)
                logger.info("[Pipeline] Sentinels sent to embed workers")
                
                # Wait for embed workers to complete
                logger.info("[Pipeline] Waiting for embed workers to complete...")
                await asyncio.gather(*embed_workers)
                logger.info("[Pipeline] All embed workers finished")
                
                # Signal DB writer that no more embeddings are coming
                logger.info("[Pipeline] Signaling DB writer to finish...")
                await vector_queue.put(None)
                logger.info("[Pipeline] Sentinel sent to DB writer")
                
                # Wait for DB writer and minister queue to drain (wait for db_writer task indirectly)
                logger.info("[Pipeline] Waiting for remaining tasks to complete...")
                try:
                    await asyncio.wait_for(
                        asyncio.gather(db_writer, minister_task),
                        timeout=30.0
                    )
                    logger.info("[Pipeline] All tasks completed successfully")
                except asyncio.TimeoutError:
                    logger.warning("[Pipeline] Some tasks timed out, cancelling...")
                    db_writer.cancel()
                    minister_task.cancel()
                    try:
                        await asyncio.gather(db_writer, minister_task)
                    except asyncio.CancelledError:
                        pass
        
        # Close DB
        await self.close_db()
        
        # Report metrics
        self.metrics.print_report()
        return self.metrics.report()


async def main_ingest(
    book_paths: List[str],
    parse_func: Callable,
    db_dsn: Optional[str] = None,
    output_root: str = "data/ministers",
    num_embed_workers: int = MAX_EMBED_CONCURRENCY,
    llm_client: Optional[Any] = None,
) -> dict:
    """High-level function to run async ingestion.
    
    Args:
        book_paths: List of book file paths
        parse_func: Function to parse book file into Chunks
        db_dsn: Optional Postgres DSN (e.g., "postgresql://user:pass@localhost/db")
        output_root: Output directory for minister consolidations
        num_embed_workers: Number of concurrent embedding workers
    
    Returns:
        Final metrics dictionary
    """
    pipeline = AsyncIngestionPipeline(db_dsn=db_dsn, output_root=output_root, llm_client=llm_client)
    return await pipeline.run(book_paths, parse_func, num_embed_workers)


__all__ = ["AsyncIngestionPipeline", "main_ingest"]
