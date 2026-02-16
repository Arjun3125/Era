"""
═══════════════════════════════════════════════════════════════════════════════
ASYNC INGESTION PIPELINE - COMPREHENSIVE ARCHITECTURE GUIDE
═══════════════════════════════════════════════════════════════════════════════

This document describes the complete async ingestion pipeline implementation
at c:\era\ingestion\v2\src\ following first-principles optimization patterns.

═══════════════════════════════════════════════════════════════════════════════
I. OVERALL ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

The system uses a multi-stage async pipeline that overlaps CPU, network, and
disk I/O operations to maximize throughput while respecting rate limits.

TOPOLOGY:
                                
    Book Reader Pool (CPU-bound with ProcessPoolExecutor)
            │
            ↓
        [chunk_queue] (bounded, max 1000)
            │
    ┌───────┼───────┐
    │       │       │
 ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
 │Embed│ │Embed│ │Embed│  Embedding Workers (async, 2-50 concurrent)
 │ W1  │ │ W2  │ │ Wn  │  - Batches chunks (64 per batch)
 └──┬──┘ └──┬──┘ └──┬──┘  - Handles rate limiting
    │       │       │    - Adaptive concurrency control
    └───────┼───────┘
            ↓
        [vector_queue] (bounded, max 1000)
            │
        ┌───▼────┐
        │DB Bulk │  DB Writer (asyncpg bulk copy)
        │ Writer │  - Batches inserts (200 records)
        └───┬────┘  - Uses transactions
            │
        [minister_queue] (bounded, max 1000)
            │
        ┌───▼──────────┐
        │  Minister    │  Minister Aggregator
        │ Aggregator   │  - Buffers by domain (100 chunks)
        └──────┬───────┘  - Consolidated JSON per domain/category
               │
        Output: data/test_ministers/{domain}/{category}.json


KEY QUEUES (all bounded for backpressure):
  - chunk_queue: parsed chunks from readers
  - vector_queue: chunks with embeddings
  - minister_queue: chunks ready for aggregation


═══════════════════════════════════════════════════════════════════════════════
II. MODULE REFERENCE
═══════════════════════════════════════════════════════════════════════════════

1. async_ingest_config.py
   ────────────────────────
   
   Configuration constants:
   - MAX_EMBED_CONCURRENCY: Initial concurrent embed workers (default 20)
   - EMBED_BATCH_SIZE: Chunks per embedding call (default 64)
   - DB_BATCH_SIZE: Records per DB insert batch (default 200)
   - MINISTER_BATCH_SIZE: Chunks before flushing domain buffer (default 100)
   - QUEUE_MAXSIZE: Max items in queues before blocking (default 1000)
   
   Data Models:
   - Chunk: Represents a parsed chunk from a book
     * id: UUID
     * text: actual content
     * domain: semantic domain (strategy, base, conflict, etc.)
     * category: entry type (principles, rules, claims, warnings)
     * embedding: list of floats (set by embed worker)
     * metadata: dict for custom fields
     * source_book, source_chapter: provenance


2. rate_controller.py
   ──────────────────
   
   AdaptiveRateController class:
   
   Features:
   - Dynamically adjusts concurrency based on API feedback
   - Monitors rate limits (429 errors) and response latency
   - Implements exponential backoff on errors
   
   Methods:
   - record_success(latency): Mark successful call
   - record_rate_limit(): Mark 429 error
   - adjust(): Recalculate concurrency (run periodically)
   - acquire/release(): Semaphore control
   
   Behavior:
   - Low latency (< 0.6s) → increase concurrency (up to + 2 workers)
   - High latency (> 1.2s) → decrease concurrency (0.9x)
   - Rate limit hits (>= 3) → aggressive backoff (0.7x)
   - Backoff sleep: exponential, capped at 32 seconds


3. ingest_metrics.py
   ──────────────────
   
   IngestMetrics class:
   
   Tracks:
   - Throughput (chunks/sec)
   - Per-stage latencies (embed, DB, minister)
   - Error counts, rate limit hits, dropped chunks
   - Memory usage via deque rotation
   
   Methods:
   - record_embed(latency), record_db(latency), record_minister(latency)
   - record_processed(count), record_dropped(count)
   - get_throughput(), get_avg_*_latency()
   - report(): Generate metrics dict
   - print_report(): Pretty-print to console


4. async_workers.py
   ────────────────
   
   Reader Worker (CPU-bound):
   - Offloads file parsing to ProcessPoolExecutor to avoid blocking event loop
   - Parses a book file into Chunk objects
   - Forwards chunks to chunk_queue
   
   Embed Worker (Network-bound):
   - Collects EMBED_BATCH_SIZE chunks from queue
   - Calls embedding API (batched, e.g., OpenAI embeddings)
   - Uses rate_controller.acquire() to respect rate limits
   - Inserts embedding into Chunk.embedding
   - Forwards to vector_queue
   - Periodic rate controller adjustment (every 5 batches)
   
   DB Bulk Writer:
   - Collects DB_BATCH_SIZE chunks from vector_queue
   - If DB pool (asyncpg) available: uses bulk copy
   - Else: falls back to VectorDBStub (file-backed)
   - Forwards to minister_queue
   
   Minister Aggregator:
   - Buffers chunks by domain
   - Flushes to consolidated JSON when buffer reaches MINISTER_BATCH_SIZE
   - Per-category JSON: {domain}/{category}.json


5. async_ingest_orchestrator.py
   ─────────────────────────────
   
   AsyncIngestionPipeline class:
   
   Methods:
   - __init__(db_dsn, output_root): Set up (DSN optional)
   - initialize_db(): Create asyncpg pool or use stub
   - run(book_paths, parse_func, num_embed_workers): Execute pipeline
   
   main_ingest(...): High-level entry point
   
   Flow:
   1. Initialize DB connection pool (if DSN provided)
   2. Create bounded queues
   3. Spawn reader tasks (one per book)
   4. Spawn embed workers (N tasks)
   5. Spawn DB writer task
   6. Spawn minister aggregator task
   7. Wait for all readers to finish
   8. Drain chunk_queue
   9. Send sentinels to embed workers
   10. Drain vector_queue
    11. Drain minister_queue
    12. Report metrics


═══════════════════════════════════════════════════════════════════════════════
III. PERFORMANCE CHARACTERISTICS
═══════════════════════════════════════════════════════════════════════════════

Expected Throughput:

Scenario                    Throughput
────────────────────────────────────────────────────────
2 embed workers, batch 64      2k–5k chunks/min
5 embed workers, batch 64      5k–10k chunks/min
10 embed workers, batch 64     10k–20k chunks/min
20 embed workers, batch 64     API rate-limited ceiling

Latency Breakdown (per chunk, weighted):

  Embedding call:    60–85% of wall time (100–500ms per call, batched)
  DB write:          10–20% (1–5ms per chunk, bulk)
  Minister agg:      ~5% (JSON consolidation, batched)
  Parsing:           5–15% (depends on book format, CPU-bound)

Scaling Limits:

  The system scales nearly linearly until hitting the LLM API rate ceiling.
  With rate-adaptive control, it self-regulates to stay just under limits.

Memory Usage:

  Queue backpressure prevents runaway memory growth.
  With QUEUE_MAXSIZE=1000, typical memory overhead ~50–200MB depending on
  chunk text size and embedding dimensions.


═══════════════════════════════════════════════════════════════════════════════
IV. CONFIGURATION & TUNING
═══════════════════════════════════════════════════════════════════════════════

Edit async_ingest_config.py to adjust:

For higher throughput (if not hitting API rate limits):
  - MAX_EMBED_CONCURRENCY: increase to 30–50
  - EMBED_BATCH_SIZE: increase to 128 (if API supports)
  - DB_BATCH_SIZE: increase to 500
  - QUEUE_MAXSIZE: increase to 2000

For lower latency/memory (e.g., on constrained hardware):
  - MAX_EMBED_CONCURRENCY: decrease to 5–10
  - EMBED_BATCH_SIZE: decrease to 32
  - DB_BATCH_SIZE: decrease to 50
  - QUEUE_MAXSIZE: decrease to 500

For rate limit robustness:
  - Adjust LATENCY_LOWER_THRESHOLD down if API is conservative
  - Adjust LATENCY_UPPER_THRESHOLD up if API can handle quick responses


═══════════════════════════════════════════════════════════════════════════════
V. INTEGRATION WITH EXISTING SYSTEM
═══════════════════════════════════════════════════════════════════════════════

The async pipeline is designed to integrate with the existing ingestion:

1. Replace existing ingest_pipeline.py entry point with:

    from async_ingest_orchestrator import main_ingest
    
    metrics = await main_ingest(
        book_paths=[...],
        parse_func=your_parse_function,
        db_dsn="postgresql://...",  # Optional; uses stub if not provided
        output_root="data/ministers",
        num_embed_workers=20
    )

2. The parse_func should return a list of Chunk objects:
    
    def parse_book(path: str) -> List[Chunk]:
        chunks = []
        for item in parse_items(path):
            chunk = Chunk(
                text=item['text'],
                domain=item['domain'],
                category=item['category'],
                metadata=item.get('meta', {})
            )
            chunks.append(chunk)
        return chunks

3. Embeddings are handled by embed_worker; configure your API key/endpoint
   in the embed_batch() function or env variables.

4. Database writes go to either PostgreSQL (asyncpg) or VectorDBStub
   (file-backed). Set db_dsn to connect to Postgres:
   
    db_dsn = "postgresql://user:password@localhost:5432/mydatabase"

5. Minister aggregator outputs consolidated JSON. Integrate with your
   downstream processing (e.g., capital_allocation.ingest_post_phase3).


═══════════════════════════════════════════════════════════════════════════════
VI. TESTING & DEBUGGING
═══════════════════════════════════════════════════════════════════════════════

Test files:

  test_async_ingest.py
    - Imports all modules
    - Tests metrics collection
    - Tests rate controller adaptation
    - Tests Chunk dataclass
    - Full pipeline integration test

  demo_async_pipeline.py
    - Standalone demo with stub parser
    - Generates synthetic chunks
    - Reports metrics

Run tests:

    python c:\era\ingestion\v2\src\test_async_ingest.py

Run demo:

    python c:\era\ingestion\v2\src\demo_async_pipeline.py

Enable debug logging:

    import logging
    logging.basicConfig(level=logging.DEBUG)


═══════════════════════════════════════════════════════════════════════════════
VII. ADVANCED FEATURES (FUTURE)
═══════════════════════════════════════════════════════════════════════════════

1. Distributed Task Queue

   Replace bounded queues with Redis queues (RQ or Celery).
   Allows scaling to multiple machines.

2. Separate Embedding Service

   Move embed_worker to its own microservice container.
   Simplifies rate limiting (single controller per svc).
   Enables language model caching (e.g., vLLM).

3. Observable Metrics

   Expose metrics endpoint to Prometheus.
   Grafana dashboard for real-time monitoring.
   Alerts on rate limits, latency spikes, errors.

4. Fault Tolerance

   Implement checkpointing (e.g., "processed up to chunk N").
   Resume on failure without re-processing.
   Dead-letter queue for permanently failed items.

5. Auto-scaling

   Monitor queue backlog.
   Spawn/kill workers dynamically based on load.


═══════════════════════════════════════════════════════════════════════════════
VIII. TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

Problem: Low throughput
  → Check avg_embed_latency_ms; if high (>1s), may be network-bound
  → Verify rate controller is increasing concurrency
  → Increase EMBED_BATCH_SIZE if API supports it
  → Check if embedding service is the bottleneck

Problem: Memory growth
  → Check queue.maxsize settings; may need to lower
  → Verify chunks are flowing through all stages
  → Check for memory leaks in custom parsing code

Problem: Rate limit errors
  → reduce MAX_EMBED_CONCURRENCY
  → reduce EMBED_BATCH_SIZE
  → check LLM API rate limits documentation

Problem: DB writes timeout
  → Increase asyncpg pool max_size
  → reduce DB_BATCH_SIZE
  → check Postgres connection/performance

Problem: Missing output files
  → Verify minister_queue is being drained (check logs)
  → Ensure output_root directory is writable
  → Check for exceptions in minister_aggregator logs


═══════════════════════════════════════════════════════════════════════════════
IX. SUMMARY: WHY THIS ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

Why Async?
  - Network calls dominate (LLM embeddings). Async prevents blocking.

Why Multiple Stages?
  - CPU (parsing) can run while network is waiting.
  - DB writes don't block embedding calls.
  - Natural backpressure via bounded queues.

Why Batching?
  - Reduces API round trips (5–10x throughput improvement alone)
  - Bulk DB inserts faster than per-row commits

Why Adaptive Rate Control?
  - Self-regulates to API's capacity without manual tuning
  - Prevents 429 storms
  - Increases throughput when capacity available

Why Consolidation Over Per-Item Files?
  - File I/O overhead dominates on some systems
  - Consolidated JSON easier to read/query
  - Enables bulk operations (rename domains, etc.)

Result: 10–20x throughput improvement over naive synchronous ingestion.


═══════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(__doc__)
