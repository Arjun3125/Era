"""Async workers for parallel Phase 2 doctrine extraction."""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable

from .async_ingest_config import QUEUE_MAXSIZE
from .rate_controller import AdaptiveRateController
from .ingest_metrics import IngestMetrics
from .doctrine_extractor import extract_doctrine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def doctrine_worker(
    chapter_queue: asyncio.Queue,
    result_queue: asyncio.Queue,
    client: Any,
    rate_controller: AdaptiveRateController,
    metrics: IngestMetrics,
    progress_cb: Optional[Callable] = None,
    storage: Optional[str] = None,
    worker_id: int = 0,
):
    """
    Doctrine extraction worker: processes chapters from a queue.
    
    Uses rate control to avoid overwhelming local Ollama instance.
    Maintains full validation and retry logic (no quality reduction).
    
    Args:
        chapter_queue: Queue of chapters to extract
        result_queue: Queue to put results
        client: OllamaClient instance
        rate_controller: Rate limiter (adaptive concurrency)
        metrics: Metrics tracker
        progress_cb: Optional progress callback
        storage: Storage directory for checkpoints
        worker_id: Worker identifier for logging
    """
    while True:
        try:
            # Diagnostic: queue sizes before attempting to get
            try:
                cq = chapter_queue.qsize()
            except Exception:
                cq = -1
            try:
                rq = result_queue.qsize()
            except Exception:
                rq = -1
            print(f"[Worker {worker_id}] chapter_queue_size={cq} result_queue_size={rq}", flush=True)

            # Get chapter with timeout
            chapter = await asyncio.wait_for(chapter_queue.get(), timeout=5.0)

            # Check for sentinel (None) to exit
            if chapter is None:
                chapter_queue.task_done()
                print(f"[Worker {worker_id}] Received sentinel, exiting", flush=True)
                break
            
            # Diagnostics: show waiting for rate slot
            print(f"[Worker {worker_id}] Waiting for rate slot...", flush=True)
            # Acquire rate control slot (throttles if Ollama is slow)
            await rate_controller.acquire()
            # Acquired slot
            chapter_index = chapter.get("chapter_index", "?")
            print(f"[Worker {worker_id}] Acquired slot. Processing chapter {chapter_index}", flush=True)
            logger.info(f"[Doctrine Worker {worker_id}] Starting chapter {chapter_index}")
            
            try:
                # Diagnostics before LLM call
                print(f"[Worker {worker_id}] Calling LLM...", flush=True)
                # Extract doctrine with FULL validation (no shortcuts)
                start_time = asyncio.get_event_loop().time()
                
                # Run extraction in executor to avoid blocking event loop
                loop = asyncio.get_running_loop()
                
                def _extract():
                    return extract_doctrine(
                        chapter,
                        client=client,
                        progress_cb=progress_cb,
                        storage=storage,
                    )
                
                doctrine = await loop.run_in_executor(None, _extract)
                
                latency = asyncio.get_event_loop().time() - start_time
                
                # Record success with original latency logic
                rate_controller.record_success(latency)
                metrics.record_processed(1)
                
                logger.info(
                    f"[Doctrine Worker {worker_id}] Completed chapter {chapter_index} "
                    f"in {latency:.2f}s (concurrency={rate_controller.concurrency})"
                )
                
                # Put result in result queue
                await result_queue.put((chapter_index, doctrine))
                print(f"[Worker {worker_id}] Result queued for chapter {chapter_index}", flush=True)
                
            except Exception as e:
                logger.error(f"[Doctrine Worker {worker_id}] Failed chapter {chapter_index}: {e}")
                metrics.record_error()
                # Put error marker
                await result_queue.put((chapter_index, {"_error": str(e)}))
            
            finally:
                chapter_queue.task_done()
                # Release the rate control slot so other workers can proceed
                try:
                    rate_controller.release()
                except Exception:
                    pass
                print(f"[Worker {worker_id}] Released slot for chapter {chapter_index}", flush=True)
                # Periodic rate adjustment
                if metrics.processed % 5 == 0:
                    rate_controller.adjust()
        
        except asyncio.TimeoutError:
            # Queue timeout, check for more work
            continue
        except Exception as e:
            logger.error(f"[Doctrine Worker {worker_id}] Unexpected error: {e}")
            metrics.record_error()


async def run_async_doctrine_extraction(
    chapters: List[Dict[str, Any]],
    client: Any,
    progress_cb: Optional[Callable] = None,
    storage: Optional[str] = None,
    num_workers: int = 1,
) -> List[Dict[str, Any]]:
    """
    Orchestrate parallel doctrine extraction for all chapters.
    
    Maintains extraction order and handles errors gracefully.
    
    Args:
        chapters: List of chapter dicts to extract
        client: OllamaClient instance
        progress_cb: Optional progress callback
        storage: Storage directory
        num_workers: Number of concurrent workers (default 2 to avoid Ollama strain)
        
    Returns:
        List of doctrine dicts in original chapter order
    """
    if not chapters:
        return []
    
    # Create queues
    chapter_queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    result_queue = asyncio.Queue()
    
    # Create rate controller (lighter than Phase 3)
    rate_controller = AdaptiveRateController(
        initial_concurrency=min(num_workers, 2),
        max_concurrency=num_workers,
        min_concurrency=1,
    )
    
    # Create metrics
    metrics = IngestMetrics()
    
    # Create worker tasks
    workers = [
        asyncio.create_task(
            doctrine_worker(
                chapter_queue,
                result_queue,
                client,
                rate_controller,
                metrics,
                progress_cb,
                storage,
                worker_id=i,
            )
        )
        for i in range(num_workers)
    ]
    
    # Queue all chapters
    for chapter in chapters:
        await chapter_queue.put(chapter)
    
    # Signal workers to exit
    for _ in range(num_workers):
        await chapter_queue.put(None)
    
    # Wait for workers to finish
    await asyncio.gather(*workers)
    
    # Collect results in original order
    total_chapters = len(chapters)
    results_by_index = {}
    
    while len(results_by_index) < total_chapters:
        try:
            chapter_index, doctrine = await asyncio.wait_for(result_queue.get(), timeout=5.0)
            results_by_index[chapter_index] = doctrine
        except asyncio.TimeoutError:
            break
    
    # Reconstruct in original order
    doctrines = []
    for chapter in chapters:
        chapter_index = chapter.get("chapter_index")
        if chapter_index in results_by_index:
            doctrines.append(results_by_index[chapter_index])
        else:
            # Missing result, create empty doctrine
            logger.warning(f"Missing result for chapter {chapter_index}")
            doctrines.append({
                "chapter_index": chapter_index,
                "chapter_title": chapter.get("chapter_title"),
                "domains": [],
                "principles": [],
                "rules": [],
                "claims": [],
                "warnings": [],
                "_status": "extraction_failed",
            })
    
    # Log metrics
    logger.info(f"[Doctrine Extraction] Processed {metrics.processed} chapters with {metrics.errors} errors")
    print(f"[Doctrine Extraction] Worker group completed. Processed={metrics.processed} errors={metrics.errors}", flush=True)
    
    return doctrines
