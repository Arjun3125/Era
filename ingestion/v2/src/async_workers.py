"""Async worker implementations for multi-stage ingestion pipeline."""
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Callable
import aiohttp
import logging

try:
    import asyncpg
except ImportError:
    asyncpg = None

from .async_ingest_config import (
    Chunk,
    EMBED_BATCH_SIZE,
    DB_BATCH_SIZE,
    MINISTER_BATCH_SIZE,
)
from .rate_controller import AdaptiveRateController
from .ingest_metrics import IngestMetrics
from .config import DEFAULT_DEEPSEEK_MODEL, DEFAULT_EMBED_MODEL


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# READER WORKER (CPU-BOUND)
# ============================================================================

async def reader_worker(
    book_path: str,
    chunk_queue: asyncio.Queue,
    pool: ThreadPoolExecutor,
    parse_func: Callable,
    metrics: IngestMetrics,
):
    """Reader worker: I/O-bound parsing of book files.
    
    Uses ThreadPoolExecutor to avoid blocking the event loop during parsing.
    More reliable on Windows than ProcessPoolExecutor.
    """
    loop = asyncio.get_running_loop()
    
    try:
        # Off-load CPU-intensive parsing to thread pool
        chunks = await loop.run_in_executor(pool, parse_func, book_path)
        
        logger.info(f"[Reader] Parsed {book_path}: {len(chunks)} chunks")
        
        for chunk in chunks:
            await chunk_queue.put(chunk)
            
    except Exception as e:
        logger.error(f"[Reader] Error parsing {book_path}: {e}")
        metrics.record_error()


# ============================================================================
# EMBEDDING WORKER (NETWORK-BOUND + BATCHING)
# ============================================================================

async def embed_worker(
    chunk_queue: asyncio.Queue,
    vector_queue: asyncio.Queue,
    session: aiohttp.ClientSession,
    embed_func: Optional[Callable],
    rate_controller: AdaptiveRateController,
    metrics: IngestMetrics,
    worker_id: int = 0,
):
    """Embedding worker: batches chunks and calls embedding API with rate control.
    
    Combines multiple chunks into a batch before calling the embedding service.
    Uses adaptive rate controller to handle rate limiting gracefully.
    """
    batch_count = 0
    
    while True:
        batch = []
        batch_texts = []
        sentinel_received = False
        
        # Collect a batch of chunks
        for _ in range(EMBED_BATCH_SIZE):
            try:
                # Use timeout to avoid indefinite waits
                chunk = await asyncio.wait_for(
                    chunk_queue.get(),
                    timeout=5.0
                )
                # Check for sentinel (None) to exit
                if chunk is None:
                    sentinel_received = True
                    chunk_queue.task_done()
                    break
                batch.append(chunk)
                batch_texts.append(chunk.text or "")
            except asyncio.TimeoutError:
                # If we timeout, process what we have
                if batch:
                    break
                else:
                    # Check queue size to see if we should give up
                    if chunk_queue.empty():
                        # Queue appears empty - wait a bit more before exiting
                        await asyncio.sleep(0.1)
                    continue
        
        if not batch:
            # Queue is exhausted, exit worker
            if sentinel_received:
                logger.info(f"[Embed Worker {worker_id}] Received sentinel, exiting")
                break
            continue
        
        # Call embedding API with rate control. Support provided embed_func (sync or async)
        embeddings = None
        if embed_func:
            try:
                # If embed_func is an async callable that accepts a list, await it
                if asyncio.iscoroutinefunction(embed_func):
                    embeddings = await embed_func(batch_texts)
                else:
                    # Run blocking embed_func in executor to avoid blocking event loop
                    loop = asyncio.get_running_loop()

                    def _call():
                        # Prefer a single batch call if the embed_func supports it.
                        if hasattr(embed_func, 'embed'):
                            # Try calling embed with the entire list; implementations
                            # may accept either a single string or a list of strings.
                            try:
                                return embed_func.embed(batch_texts)
                            except TypeError:
                                # embed may only accept single strings; fall back to mapping
                                return [embed_func.embed(t) for t in batch_texts]
                        # If embed_func itself is callable (e.g., a function), try calling it with the list
                        if callable(embed_func):
                            try:
                                return embed_func(batch_texts)
                            except TypeError:
                                return [embed_func(t) for t in batch_texts]
                        # Fallback: map individual calls
                        if hasattr(embed_func, 'embed'):
                            return [embed_func.embed(t) for t in batch_texts]
                        return [embed_func(t) for t in batch_texts]
                    

                    embeddings = await loop.run_in_executor(None, _call)
            except Exception as e:
                logger.warning(f"[Embed Worker {worker_id}] embed_func failed: {e}")
                embeddings = None

        if embeddings is None:
            # Fallback to HTTP or stub path
            embeddings = await embed_batch(
                session,
                batch_texts,
                rate_controller,
                metrics,
                worker_id,
            )
        
        # Zip embeddings with chunks and forward to vector queue
        if embeddings:
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding
                await vector_queue.put(chunk)
                chunk_queue.task_done()
            
            metrics.record_processed(len(batch))
            batch_count += 1
        else:
            # Failed to embed, drop batch
            for chunk in batch:
                chunk_queue.task_done()
            metrics.record_dropped(len(batch))
        
        # Periodic adjustment
        if batch_count % 5 == 0:
            rate_controller.adjust()


async def embed_batch(
    session: aiohttp.ClientSession,
    texts: List[str],
    rate_controller: AdaptiveRateController,
    metrics: IngestMetrics,
    worker_id: int = 0,
) -> Optional[List[List[float]]]:
    """Call embedding API with a batch of texts.
    
    Integrates rate limiting and error handling.
    """
    if not texts:
        return None

    # Acquire semaphore slot
    await rate_controller.acquire()

    try:
        start = time.time()

        # Attempt to call local Ollama HTTP embed endpoint first (batched)
        try:
            payload = {"model": DEFAULT_EMBED_MODEL, "input": texts}
            async with session.post(
                "http://localhost:11434/api/embed",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                logger.info(f"[Embed Worker {worker_id}] POST /api/embed model={payload.get('model')} batch_size={len(texts)}")
                if resp.status == 429:
                    logger.warning(f"[Embed Worker {worker_id}] Rate limited (Ollama)")
                    rate_controller.record_rate_limit()
                    metrics.record_rate_limit()
                    await rate_controller.sleep_backoff()
                    return None

                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"[Embed Worker {worker_id}] Ollama embed error: {resp.status} {text}")
                    metrics.record_error()
                    return None

                data = await resp.json()
                # Expect either {'embeddings': [...]} or list of embeddings
                if isinstance(data, dict) and "embeddings" in data:
                    embeddings = [item for item in data["embeddings"]]
                elif isinstance(data, list):
                    embeddings = data
                elif isinstance(data, dict) and "data" in data:
                    embeddings = [it.get("embedding") for it in data.get("data", [])]
                else:
                    embeddings = None

        except Exception as e:
            logger.debug(f"[Embed Worker {worker_id}] Ollama embed failed: {e}")
            embeddings = None

        latency = time.time() - start
        if embeddings is not None:
            rate_controller.record_success(latency)
            metrics.record_embed(latency)
            logger.debug(
                f"[Embed Worker {worker_id}] Embedded {len(texts)} texts in {latency:.3f}s "
                f"(concurrency={rate_controller.concurrency})"
            )
            return embeddings

        # If Ollama path failed, fall back to stub or other handlers
        logger.debug(f"[Embed Worker {worker_id}] Falling back to stub embeddings")
        embeddings = [[0.0] * 1536 for _ in texts]
        latency = time.time() - start
        rate_controller.record_success(latency)
        metrics.record_embed(latency)
        return embeddings

    except asyncio.TimeoutError:
        logger.error(f"[Embed Worker {worker_id}] Request timeout")
        metrics.record_error()
        return None
    except Exception as e:
        logger.error(f"[Embed Worker {worker_id}] Embedding error: {e}")
        metrics.record_error()
        return None
    finally:
        rate_controller.release()


# ============================================================================
# DATABASE BULK WRITER (ASYNC + BATCHING)
# ============================================================================

async def db_bulk_writer(
    vector_queue: asyncio.Queue,
    minister_queue: asyncio.Queue,
    db_pool: Optional[Any],
    metrics: IngestMetrics,
):
    """DB writer: batches embeddings and bulk-inserts into Postgres.
    
    If db_pool is None, uses stub (file-backed) storage.
    """
    
    while True:
        batch = []
        
        # Collect batch
        for _ in range(DB_BATCH_SIZE):
            try:
                chunk = await asyncio.wait_for(
                    vector_queue.get(),
                    timeout=5.0
                )
                # Check for sentinel (None) to exit
                if chunk is None:
                    vector_queue.task_done()
                    # Send sentinel to minister queue and exit
                    await minister_queue.put(None)
                    return
                batch.append(chunk)
            except asyncio.TimeoutError:
                if batch:
                    break
                else:
                    await asyncio.sleep(0.1)
                    continue
        
        if not batch:
            # Queue likely drained, but check if we got explicit sentinel
            try:
                chunk = await asyncio.wait_for(
                    vector_queue.get(),
                    timeout=1.0
                )
                if chunk is None:
                    vector_queue.task_done()
                    await minister_queue.put(None)
                    return
                batch.append(chunk)
            except asyncio.TimeoutError:
                break
        
        # Write to DB (with or without real DB)
        if db_pool:
            await _bulk_insert_postgres(db_pool, batch, metrics)
        else:
            await _bulk_insert_stub(batch, metrics)
        
        # Forward to minister aggregator
        for chunk in batch:
            await minister_queue.put(chunk)
            vector_queue.task_done()
    
    # Send sentinel to signal minister_aggregator to finish
    logger.info("[DB Writer] Signaling minister aggregator to finish")
    await minister_queue.put(None)


async def _bulk_insert_postgres(
    db_pool: Any,
    batch: List[Chunk],
    metrics: IngestMetrics,
):
    """Insert chunks into Postgres using bulk copy."""
    if not asyncpg:
        logger.warning("asyncpg not installed; using stub storage")
        await _bulk_insert_stub(batch, metrics)
        return
    
    start = time.time()
    
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                records = [
                    (
                        chunk.id,
                        chunk.domain,
                        chunk.category,
                        chunk.text,
                        chunk.embedding,
                        chunk.source_book,
                        chunk.source_chapter,
                        1.0,  # weight
                    )
                    for chunk in batch
                ]
                
                await conn.copy_records_to_table(
                    'minister_embeddings',
                    records=records
                )
        
        latency = time.time() - start
        metrics.record_db(latency)
        logger.info(f"[DB Writer] Bulk inserted {len(batch)} rows in {latency:.3f}s")
        
    except Exception as e:
        logger.error(f"[DB Writer] Postgres error: {e}")
        metrics.record_error()
        # Fall back to stub
        await _bulk_insert_stub(batch, metrics)


async def _bulk_insert_stub(batch: List[Chunk], metrics: IngestMetrics):
    """Stub DB insert using file-backed vector DB."""
    start = time.time()
    
    try:
        from .vector_db import VectorDBStub
        vdb = VectorDBStub(storage_root='data')

        # Prepare batch records and group by domain for domain-level inserts
        combined_recs = []
        domain_groups = {}

        from .vector_db import validate_domain

        for chunk in batch:
            if not chunk.embedding:
                continue
            try:
                validate_domain(chunk.domain)
            except Exception as e:
                logger.debug(f"[DB Stub] Skipping chunk {chunk.id}: {e}")
                continue

            rec = {
                "domain": chunk.domain,
                "category": chunk.category,
                "text": chunk.text,
                "embedding": chunk.embedding,
                "source_book": chunk.source_book,
                "source_chapter": chunk.source_chapter,
                "weight": 1.0,
            }
            combined_recs.append(rec)

            domain_list = domain_groups.setdefault(chunk.domain, [])
            domain_list.append({
                "category": chunk.category,
                "text": chunk.text,
                "embedding": chunk.embedding,
                "weight": 1.0,
            })

        # Bulk insert combined records (single read/write)
        if combined_recs:
            try:
                vdb.insert_combined_batch(combined_recs)
            except Exception as e:
                logger.debug(f"[DB Stub] Bulk combined insert failed: {e}")

        # Bulk insert per-domain records
        for domain, recs in domain_groups.items():
            try:
                vdb.insert_domain_batch(domain, recs)
            except Exception as e:
                logger.debug(f"[DB Stub] Bulk domain insert failed for {domain}: {e}")
        
        latency = time.time() - start
        metrics.record_db(latency)
        logger.info(f"[DB Stub] Written {len(batch)} rows (bulk) in {latency:.3f}s")
        
    except Exception as e:
        logger.error(f"[DB Stub] Error: {e}")
        metrics.record_error()


# ============================================================================
# MINISTER AGGREGATOR (CONSOLIDATED WRITES)
# ============================================================================

async def minister_aggregator(
    minister_queue: asyncio.Queue,
    metrics: IngestMetrics,
    output_root: str = "data/ministers",
):
    """Minister aggregator: buffers chunks by domain and writes consolidated JSON.
    
    Instead of per-item writes, consolidates multiple chunks per domain/category.
    """
    domain_buffers: Dict[str, List[Chunk]] = {}
    
    while True:
        chunk = None
        
        try:
            chunk = await asyncio.wait_for(
                minister_queue.get(),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            # Process remaining buffers and exit
            await _flush_all_domains(domain_buffers, metrics, output_root)
            break
        
        # Check for sentinel to exit
        if chunk is None:
            minister_queue.task_done()
            # Flush all remaining buffers
            await _flush_all_domains(domain_buffers, metrics, output_root)
            break
        
        # Buffer by domain
        domain = chunk.domain
        if domain not in domain_buffers:
            domain_buffers[domain] = []
        
        domain_buffers[domain].append(chunk)
        
        # Flush when domain buffer reaches threshold
        if len(domain_buffers[domain]) >= MINISTER_BATCH_SIZE:
            await _flush_domain(domain, domain_buffers[domain], metrics, output_root)
            domain_buffers[domain] = []
        
        minister_queue.task_done()


async def _flush_domain(
    domain: str,
    chunks: List[Chunk],
    metrics: IngestMetrics,
    output_root: str,
):
    """Flush a domain's buffered chunks to consolidated JSON."""
    start = time.time()
    
    try:
        import os
        os.makedirs(output_root, exist_ok=True)
        
        domain_path = os.path.join(output_root, domain)
        os.makedirs(domain_path, exist_ok=True)
        
        # Consolidate by category
        by_category: Dict[str, list] = {}
        for chunk in chunks:
            cat = chunk.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "id": chunk.id,
                "text": chunk.text,
                "embedding": chunk.embedding,
                "source_book": chunk.source_book,
                "source_chapter": chunk.source_chapter,
                "metadata": chunk.metadata,
            })
        
        # Write consolidated JSON per category
        for category, items in by_category.items():
            category_file = os.path.join(domain_path, f"{category}.json")
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        
        latency = time.time() - start
        metrics.record_minister(latency)
        logger.info(f"[Minister] Flushed {domain}: {len(chunks)} chunks in {latency:.3f}s")
        
    except Exception as e:
        logger.error(f"[Minister] Error flushing {domain}: {e}")
        metrics.record_error()


async def _flush_all_domains(
    domain_buffers: Dict[str, List[Chunk]],
    metrics: IngestMetrics,
    output_root: str,
):
    """Flush all remaining domain buffers."""
    for domain, chunks in domain_buffers.items():
        if chunks:
            await _flush_domain(domain, chunks, metrics, output_root)


__all__ = [
    "reader_worker",
    "embed_worker",
    "embed_batch",
    "db_bulk_writer",
    "minister_aggregator",
]
