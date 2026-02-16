# Production Async Ingestion Pipeline

A production-ready, horizontally scalable ingestion system for processing document chapters through chunking, embedding, and storage with adaptive rate limiting and distributed worker orchestration.

## Overview

```
Submission Queue → Rate Controller → Pipeline Orchestrator → Worker Pools → Output
                      ↓
              Feedback Loop (Adaptive Rate)
```

### Key Features

- **Adaptive Rate Control**: Token-bucket rate limiter with feedback loop that adjusts throughput based on queue depth
- **Parallel Pipeline**: Multi-stage worker pools for chunking, embedding, storage (2-12 workers per stage)
- **Distributed Queue**: Redis-backed or in-memory queue with priority ordering and retry logic
- **Backpressure Handling**: Automatic slowdown when downstream queues fill up
- **Comprehensive Metrics**: Real-time throughput, latency (p95/p99), success rates
- **Benchmarking Framework**: Load testing, scaling tests, and sustained load profiles
- **Configuration Presets**: Local, Standard, and High-Throughput environment configs

## Architecture

### Components

#### 1. Adaptive Controller (`adaptive_controller.py`)
Token bucket rate limiter with feedback loop.

```python
from adaptive_controller import AdaptiveController, AdaptiveConfig

# Create with defaults
controller = AdaptiveController()

# Acquire rate permit (blocks if rate-limited)
if await controller.acquire_permit(tokens=1.0):
    # Process item
    controller.record_processing(elapsed_time, success=True)

# Update queue depth for feedback
controller.update_queue_depth(current_depth=50, max_depth=1000)

# Get metrics
metrics = controller.get_metrics()
```

**Rate Adjustment Logic:**
- High queue depth (>80%): Reduce rate by 50% 
- Low queue depth (<30%): Increase rate by 20%
- Clamped between 20%-200% of base rate

#### 2. Distributed Queue (`distributed_queue.py`)
Abstract queue interface with InMemory and Redis implementations.

```python
from distributed_queue import create_queue, QueuedItem

queue = create_queue(queue_type="memory", max_size=1000)

# Enqueue with priority
item = QueuedItem(
    id="item_1",
    data={"chapter": 5, "text": "..."},
    priority=10,  # Higher = earlier
    max_retries=3
)
await queue.enqueue(item)

# Dequeue
item = await queue.dequeue()

# Mark complete or requeue on failure
if success:
    await queue.mark_complete(item.id)
else:
    await queue.requeue_failed(item)
```

#### 3. Worker Pools (`ingest_workers.py`)
Async worker pools that process items through stages.

```python
from ingest_workers import PipelineOrchestrator, WorkerStage

# Create pipeline
pipeline = PipelineOrchestrator()

# Add stages with worker pools
pipeline.add_stage(
    stage=WorkerStage.CHUNK,
    process_fn=my_chunk_function,
    num_workers=4,
    batch_size=10
)

await pipeline.start()

# Process items
result = await pipeline.process_item({"text": "..."})

await pipeline.stop()
```

**Batch Processing:**
- Accumulates items up to batch_size before processing
- Reduces overhead, increases throughput
- Trade-off: smaller batches = lower latency

#### 4. Async Ingestion Orchestrator (`async_ingestion_orchestrator.py`)
Main orchestration layer tying everything together.

```python
from async_ingestion_orchestrator import AsyncIngestionOrchestrator

orchestrator = AsyncIngestionOrchestrator(
    chunk_workers=4,
    embed_workers=6,
    store_workers=4,
    max_queue_depth=1000
)

await orchestrator.start()

# Submit job
job_id = await orchestrator.submit_job(
    book_slug="the-richest-man",
    chapter_index=3,
    text="Chapter content...",
    priority=5
)

# Check status
status = orchestrator.get_job_status(job_id)

# Wait for completion
completed = await orchestrator.wait_for_completion(timeout=300.0)

# Get metrics
metrics = orchestrator.get_orchestrator_metrics()

await orchestrator.stop()
```

## Configuration

### Environment Presets

**Local Development** (`ingestion_config.py`):
```python
from ingestion_config import create_orchestrator_config

config = create_orchestrator_config(environment="local")
orchestrator = AsyncIngestionOrchestrator(**config)
# 2 workers per stage, batch size 5, conservative rate limiting
```

**Standard Production**:
```python
config = create_orchestrator_config(environment="standard")
# 4-6 workers per stage, batch size 4-10, balanced rate limiting
```

**High Throughput**:
```python
config = create_orchestrator_config(environment="high_throughput")
# 8-12 workers per stage, batch size 10+, aggressive rate limiting
```

### Rate Limiting Presets

```python
from adaptive_controller import AdaptiveConfig, AdaptiveControllerPresets

# Conservative: Good for testing
config = AdaptiveControllerPresets.CONSERVATIVE
# 10 tokens/sec, reduce to 30% under congestion

# Balanced: Production default
config = AdaptiveControllerPresets.BALANCED
# 50 tokens/sec, reduce to 50% under congestion

# Aggressive: High throughput
config = AdaptiveControllerPresets.AGGRESSIVE
# 200 tokens/sec, reduce to 60% under congestion
```

## Usage Examples

### Basic Ingestion

```python
import asyncio
from async_ingestion_orchestrator import AsyncIngestionOrchestrator

async def main():
    orchestrator = AsyncIngestionOrchestrator()
    await orchestrator.start()
    
    try:
        # Load chapters
        with open("chapters.json") as f:
            chapters = json.load(f)
        
        # Submit all chapters
        job_ids = []
        for chapter in chapters:
            job_id = await orchestrator.submit_job(
                book_slug="my_book",
                chapter_index=chapter["index"],
                text=chapter["text"]
            )
            job_ids.append(job_id)
        
        # Wait for completion
        await orchestrator.wait_for_completion(timeout=600.0)
        
        # Get results
        for job_id in job_ids:
            status = orchestrator.get_job_status(job_id)
            print(f"{job_id}: {status['phase']}")
        
        # Final metrics
        metrics = orchestrator.get_orchestrator_metrics()
        print(json.dumps(metrics, indent=2))
    
    finally:
        await orchestrator.stop()

asyncio.run(main())
```

### Benchmarking

```python
from benchmark_harness import BenchmarkHarness, BenchmarkPhase

harness = BenchmarkHarness(orchestrator)

# Warmup
await harness.run_test(
    test_name="Warmup",
    num_items=10,
    phase=BenchmarkPhase.WARMUP
)

# Scaling tests
await harness.run_scaling_benchmark(
    item_counts=[100, 500, 1000]
)

# Load profile
await harness.run_load_profile_benchmark(
    duration_seconds=60,
    target_throughput=50  # items/sec
)

# Save results
harness.save_results("benchmark_results.json")
```

### Custom Worker Functions

```python
from ingest_workers import WorkerStage
import numpy as np

async def my_chunk_worker(item: dict) -> dict:
    """Custom chunking logic."""
    text = item["text"]
    chunk_size = 512
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    return {**item, "chunks": chunks}

async def my_embed_worker(item: dict) -> dict:
    """Custom embedding logic."""
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    chunks = item["chunks"]
    embeddings = model.encode(chunks)  # Returns np.ndarray
    
    return {**item, "embeddings": embeddings.tolist()}

async def my_store_worker(item: dict) -> dict:
    """Custom storage logic."""
    import asyncpg
    pool = await asyncpg.create_pool("postgresql://...")
    
    async with pool.acquire() as conn:
        await conn.executemany(
            "INSERT INTO embeddings VALUES ($1, $2, $3)",
            [(item["id"], i, emb) for i, emb in enumerate(item["embeddings"])]
        )
    
    return {**item, "stored": True}

# Wire into orchestrator
orchestrator.pipeline.stages[WorkerStage.CHUNK].workers[0].process_fn = my_chunk_worker
orchestrator.pipeline.stages[WorkerStage.EMBED].workers[0].process_fn = my_embed_worker
orchestrator.pipeline.stages[WorkerStage.STORE].workers[0].process_fn = my_store_worker
```

## Deployment

### Docker Compose (Multi-Node)

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"

  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: era_ingestion
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"

  ingestion_worker_1:
    build: .
    environment:
      QUEUE_TYPE: redis
      REDIS_URL: redis://redis:6379
      DB_URL: postgresql://postgres:password@postgres:5432/era_ingestion
      WORKERS_CHUNK: 4
      WORKERS_EMBED: 6
      WORKERS_STORE: 4
    depends_on:
      - redis
      - postgres

  ingestion_worker_2:
    build: .
    # Same config, scales horizontally
    depends_on:
      - redis
      - postgres
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingestion-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ingestion
  template:
    metadata:
      labels:
        app: ingestion
    spec:
      containers:
      - name: ingestion
        image: era:ingestion
        env:
        - name: QUEUE_TYPE
          value: redis
        - name: REDIS_URL
          value: redis://redis-service:6379
        - name: WORKERS_CHUNK
          value: "4"
        - name: WORKERS_EMBED
          value: "6"
        - name: WORKERS_STORE
          value: "4"
        resources:
          requests:
            cpu: 2
            memory: 2Gi
          limits:
            cpu: 4
            memory: 4Gi
```

## Monitoring

### Metrics Available

**Ingestion Metrics:**
- `total_submitted`: Jobs submitted
- `total_completed`: Jobs successfully processed
- `total_failed`: Jobs that failed
- `throughput_items_per_sec`: Current throughput
- `success_rate_percent`: Percentage successful

**Rate Controller Metrics:**
- `current_rate_multiplier`: Current rate adjustment (0.2-2.0)
- `queue_depth`: Current items in queue
- `tokens_available`: Tokens in bucket
- `avg_processing_time_ms`: Average item processing time

**Pipeline Metrics (per stage):**
- `items_processed`: Items completed at this stage
- `items_failed`: Items failed at this stage
- `avg_time_per_item_ms`: Average processing time
- `last_item_time_ms`: Last item processing time

### Prometheus Integration

```python
# Export metrics for Prometheus scraping
from prometheus_client import Counter, Gauge, Histogram

job_counter = Counter('ingestion_jobs_submitted', 'Jobs submitted')
job_completed = Counter('ingestion_jobs_completed', 'Jobs completed')
latency_histogram = Histogram('ingestion_latency_ms', 'Item latency')
queue_depth_gauge = Gauge('ingestion_queue_depth', 'Queue depth')

# In processing loop
queue_depth_gauge.set(current_depth)
latency_histogram.observe(elapsed_ms)
job_completed.inc()
```

## Performance Tuning

### Throughput Optimization

1. **Increase Worker Count**: More workers for I/O-heavy tasks
   - Chunking: 4-8 workers (CPU-bound)
   - Embedding: 8-16 workers (Network I/O)
   - Storage: 8-16 workers (Database I/O)

2. **Increase Batch Sizes**: Larger batches reduce overhead
   - Trade-off: increases latency
   - Good balance: 10-50 items per batch

3. **Aggressive Rate Limiting**: Higher token rate
   - Start with STANDARD, increase to AGGRESSIVE
   - Monitor error rates

4. **Database Optimization**:
   - Increase connection pool size (20-50)
   - Use bulk insert operations
   - Index commonly queried fields

### Latency Optimization

1. **Reduce Batch Sizes**: Process items faster
   - Batch size 1-5 for low-latency needs
   - Trade-off: reduces throughput

2. **Conservative Rate Limiting**: Reduce queue depth
   - Use CONSERVATIVE profile
   - Prevents items queuing

3. **Reduce Worker Count**: Less queueing
   - But reduces throughput

## Testing

### Unit Tests

```bash
pytest test_async_ingestion.py -v
```

### Integration Tests

```python
# Run full pipeline test
pytest test_async_ingestion.py::TestIntegrationPipeline -v -s
```

### Load Testing

```python
asyncio.run(benchmark_harness.run_scaling_benchmark(
    item_counts=[100, 500, 1000, 5000]
))
```

## Troubleshooting

### Queue Growing / Items Not Processing

1. Check rate controller metrics
   - Is rate_multiplier very low? May indicate congestion
2. Increase worker counts
   - Bottleneck may be downstream (embedding, storage)
3. Check database/embedding service
   - Network latency or service unavailability
4. Review error logs
   - Failed items are requeued; check max retries

### High Latency

1. Increase batch sizes
   - Larger items spend more time in batch
2. Reduce worker count
   - More workers = more queueing
3. Check resource usage
   - CPU/memory saturation affects performance

### Worker Crashes

1. Check memory leaks
   - Monitor process RSS over time
2. Increase resource limits
3. Add circuit breaker for failing services

## Files

- `adaptive_controller.py` - Token bucket + feedback loop
- `distributed_queue.py` - Queue abstraction (memory/Redis)
- `ingest_workers.py` - Worker pools and pipeline orchestration
- `async_ingestion_orchestrator.py` - Main orchestrator
- `ingestion_config.py` - Configuration presets
- `benchmark_harness.py` - Performance benchmarking framework
- `test_async_ingestion.py` - Integration test suite

## Next Steps

1. **Integrate Real Worker Functions**: Replace example workers with actual chunking, embedding, storage logic
2. **Add Error Handling**: Database failures, network timeouts, malformed input
3. **Implement Checkpointing**: Resume from failure point
4. **Add Observability**: Prometheus metrics, structured logging
5. **Deploy to Kubernetes**: Multi-node scaling

## License

Same as parent ERA project
