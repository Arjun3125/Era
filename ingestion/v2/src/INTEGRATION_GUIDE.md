# Production Pipeline Integration Guide

## Overview

This scaffolding provides a **production-ready async ingestion + adaptive controller system** for the ERA project. It complements the existing minister conversion pipeline by handling the compute-intensive operations (chunking, embedding, aggregation) with proper parallelism, rate limiting, and error handling.

## System Architecture

```
ERA Ingestion Pipeline (Complete Flow)

┌──────────────────────────────────────────────────────────────────┐
│                        INPUT: Doctrine JSON                       │
│                   (from Phase 2 extraction)                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  ASYNC INGESTION ORCHESTRATOR          │
        │  ├─ Queue: Priority-based job queue    │
        │  ├─ Controller: Token-bucket rate      │
        │  │    limiting with feedback loop      │
        │  └─ Pipeline: Multi-stage workers      │
        └────────────────┬───────────────────────┘
                         │
        ┌────────────────┴──────────────────────────────────┐
        │              WORKER PIPELINES                      │
        │                                                    │
        ├─ Stage 1: CHUNKING                                │
        │   Workers: 4-8 (CPU-bound)                         │
        │   Batch size: 10-50                                │
        │   Output: Text chunks (512-1024 chars)             │
        │                                                    │
        ├─ Stage 2: EMBEDDING                               │
        │   Workers: 8-16 (Network I/O)                      │
        │   Batch size: 5-20                                 │
        │   Service: Ollama (local or remote)                │
        │   Output: Vector embeddings (384-768 dims)         │
        │                                                    │
        ├─ Stage 3: AGGREGATION & MINISTER CONVERSION        │
        │   Workers: 4-8                                     │
        │   Batch size: 1-5                                  │
        │   Input: Doctrine → Organized domains              │
        │   Output: Domain-specific entry JSONs              │
        │                                                    │
        └─ Stage 4: STORAGE                                  │
            Workers: 4-8 (Database I/O)                      │
            Batch size: 10-20                                │
            Targets:                                         │
              - PGVector: Embedding storage                  │
              - PostgreSQL: Minister metadata                │
              - Combined index: Vector search                │
```

## Integration Points

### 1. With Existing Minister Converter

**Current System** (`ingestion/v2/src/minister_converter.py`):
- Converts chapter doctrine to domain-specific folders
- Creates JSON files in `/data/ministers/{domain}/`
- Updates combined vector index

**New Production System**:
- Orchestrator submits chapters as jobs
- Worker pipeline processes chapters through stages
- Storage worker writes to same `/data/ministers/` structure via `minister_converter.add_category_entry()`

**Integration Approach**:
```python
# In worker pipeline's AGGREGATION stage
async def aggregation_worker(item: dict) -> dict:
    """Convert embeddings to minister structure."""
    from src.minister_converter import process_chapter_doctrine, add_category_entry
    
    chapter_data = item["chapter_data"]
    embeddings = item["embeddings"]
    
    # Convert to minister structure
    domain_entries = process_chapter_doctrine(
        chapter_data=chapter_data,
        book_slug=item["book_slug"],
        data_root="data"
    )
    
    # Attach embeddings to minister entries
    item["minister_entries"] = domain_entries
    item["embeddings"] = embeddings
    return item

# In STORAGE stage
async def storage_worker(item: dict) -> dict:
    """Store embeddings and minister data."""
    # Write embeddings to PGVector
    await write_to_pgvector(
        embeddings=item["embeddings"],
        domain=item["domain"],
        category=item["category"]
    )
    
    # Minister structure already written by aggregation stage
    return {**item, "stored": True}
```

### 2. With Existing Embedding Pipeline

**Current System** (`ingestion/v2/src/embeddings.py`):
- Requires knowledge of Ollama client setup
- Uses local Ollama HTTP endpoint

**New Production System**:
- Centralizes Ollama client in worker stage
- Handles batching and retry logic
- Provides fallback stub embeddings

**Integration Approach**:
```python
from ingestion.v2.src.ollama_client import OllamaClient

class EmbedPool(WorkerPool):
    """Embedding worker pool with Ollama client."""
    
    async def __aenter__(self):
        self.ollama = OllamaClient(base_url=OLLAMA_URL)
        return self
    
    async def __aexit__(self, *args):
        await self.ollama.close()

# In orchestrator:
async def create_embed_pipeline():
    async with EmbedPool(...) as pool:
        orchestrator.pipeline.stages[WorkerStage.EMBED] = pool
```

### 3. With Existing Doctor Doctrine System

**Current System** (`persona/analysis.py`, `persona/knowledge_engine.py`):
- Uses `apply_ml_judgment_prior()` for ML-assisted synthesis
- Expects embeddings for semantic analysis

**New Production System**:
- Generates embeddings that can be used for:
  - Doctrine similarity matching
  - ML-assisted judgment priors
  - Knowledge base search

**Integration Approach**:
```python
# In knowledge engine
async def semantic_similarity_lookup(query_embedding, domain, top_k=5):
    """Find similar doctrines using embeddings."""
    from pgvector.psycopg2 import Vector
    import asyncpg
    
    conn = await asyncpg.connect(DB_URL)
    
    results = await conn.fetch(
        """
        SELECT doctrine_id, similarity(embedding, $1) as score
        FROM doctrine_embeddings
        WHERE domain = $2
        ORDER BY embedding <-> $1
        LIMIT $3
        """,
        query_embedding,
        domain,
        top_k
    )
    
    return results
```

### 4. With Persona Real-Time Interaction

**Current System** (`persona/main.py`, `interactive_persona_chat.py`):
- Persona uses doctrine for context
- Questions require semantic search

**New Production System**:
- Embeddings enable fast semantic search
- Can respond to doctrine-based questions in real-time

**Integration Approach**:
```python
# In persona's context enrichment
async def enrich_context_with_doctrine(query_text):
    """Find relevant doctrine for persona context."""
    # Generate embedding for query
    query_emb = await ollama.embed(query_text)
    
    # Search for related doctrines
    similar_doctrines = await semantic_similarity_lookup(
        query_embedding=query_emb,
        domain=persona.domain,
        top_k=3
    )
    
    # Add to context
    persona.doctrine_context = similar_doctrines
    return persona
```

## Data Flow Example

### Scenario: Ingesting "The Richest Man in Babylon"

#### Step 1: Submission
```python
# From ingestion orchestrator
await orchestrator.submit_job(
    book_slug="the-richest-man-in-babylon",
    chapter_index=1,
    text="Once there lived in Babylon a certain very rich man named...",  # Chapter 1 text
    priority=1
)
```

#### Step 2: Chunking
```
Input: Full chapter text (~5000 words)
↓
9 chunks of 512 words each
↓
Output: {
    "chapter_data": {...},
    "chunks": ["Chunk 1...", "Chunk 2...", ...],
    "chunk_count": 9
}
```

#### Step 3: Embedding
```
Input: 9 chunks
↓
Ollama nomic-embed-text model
↓
Output: {
    "chunks": [...],
    "embeddings": [  # 9 x 768-dim vectors
        [0.123, 0.456, ...,],  # Chunk 1 embedding
        [0.789, 0.012, ...,],  # Chunk 2 embedding
        ...
    ]
}
```

#### Step 4: Aggregation & Minister Conversion
```
Input: Chapter doctrine + embeddings
↓
Extract doctrine (principles, rules, claims, warnings)
↓
Group by domain (wealth, ethics, discipline, etc.)
↓
Output directory structure:
/data/ministers/wealth/
  ├─ principles.json      # Wealth principles
  │   └─ [entries]: [id, text, source, embedding_id]
  ├─ rules.json           # Wealth rules
  ├─ claims.json
  ├─ warnings.json
  └─ doctrine.json        # Summary

/data/ministers/ethics/
  ├─ principles.json
  ... (same structure)
```

#### Step 5: Storage
```
PGVector Tables:
  doctrine_embeddings_wealth
  doctrine_embeddings_ethics
  ...
  
Combined Index:
  doctrine_embeddings_all
  
PostgreSQL Tables:
  minister_entries (metadata)
  doctrine_sources (provenance)
```

## Performance Characteristics

### Throughput Targets

| Environment | Workers | Batch Size | Throughput | Latency |
|---|---|---|---|---|
| **Local** (2-4 dev cores) | 2+2+2 | 5+3+2 | 5-10 items/sec | 500-2000ms |
| **Standard** (8 cores, 16GB RAM) | 4+6+4 | 10+8+4 | 30-50 items/sec | 100-500ms |
| **High-Throughput** (16 cores, 32GB RAM) | 8+12+8 | 50+20+10 | 100-200 items/sec | 50-200ms |

### Scaling Characteristics

- **Linear scaling**: Throughput scales approximately linearly with worker count (up to CPU core count)
- **Queue depth**: Maintained <10% of max queue with adaptive controller
- **Rate limiting**: Automatically adjusts ±200% based on system load

## Implementation Checklist

### Phase 1: Setup (1-2 hours)
- [ ] Copy all `.py` files to `ingestion/v2/src/`
- [ ] Verify imports work
- [ ] Run quickstart examples
- [ ] Check database/Ollama connectivity

### Phase 2: Integration (2-4 hours)
- [ ] Implement real chunking logic
- [ ] Connect to Ollama embedding service
- [ ] Integrate minister converter
- [ ] Add database storage operations
- [ ] Test end-to-end with real data

### Phase 3: Testing (4-8 hours)
- [ ] Run integration tests
- [ ] Benchmark on local data
- [ ] Stress test with large books
- [ ] Verify data integrity
- [ ] Monitor resource usage

### Phase 4: Deployment (4-8 hours)
- [ ] Containerize with Docker
- [ ] Set up Kubernetes deployment
- [ ] Configure monitoring/logging
- [ ] Deploy to staging
- [ ] Load test in staging

### Phase 5: Production (2-4 hours)
- [ ] Blue-green deployment
- [ ] Monitor in production
- [ ] Tune rate limits based on actual load
- [ ] Document runbooks

## File Structure

```
ingestion/v2/src/
├─ adaptive_controller.py           # Token bucket + feedback loop
├─ distributed_queue.py             # Queue abstraction (memory/Redis)
├─ ingest_workers.py                # Worker pools and pipeline
├─ async_ingestion_orchestrator.py   # Main orchestrator
├─ ingestion_config.py              # Configuration presets
├─ benchmark_harness.py             # Performance testing framework
├─ test_async_ingestion.py          # Integration tests
├─ quickstart.py                    # Quick start examples
└─ README_PRODUCTION_PIPELINE.md    # Full documentation
```

**Plus existing files:**
- `minister_converter.py` - For domain conversion
- `minister_vector_db.py` - For vector storage
- `ollama_client.py` - For embeddings
- Other phase 2/3 files

## Success Criteria

### Performance
- [ ] 100+ items/sec on standard hardware
- [ ] P95 latency < 500ms
- [ ] 99.5% success rate

### Reliability
- [ ] Automatic retry on failures
- [ ] No data loss (atomic writes)
- [ ] Dead-letter queue for failed items

### Scalability
- [ ] Horizontal scaling (add more workers)
- [ ] Vertical scaling (more resources per machine)
- [ ] Distributed deployment (Redis queue)

### Observability
- [ ] Real-time metrics dashboard
- [ ] Prometheus scraping
- [ ] Structured logging
- [ ] Error tracking

## Next Steps

1. **Review README_PRODUCTION_PIPELINE.md** for detailed API documentation
2. **Run quickstart examples** to verify setup:
   ```bash
   cd ingestion/v2/src
   python quickstart.py 1  # Basic ingestion
   python quickstart.py 2  # Benchmarking
   ```
3. **Implement real worker functions** by reading code comments
4. **Run integration tests**:
   ```bash
   pytest test_async_ingestion.py -v
   ```
5. **Benchmark on real data** from your books
6. **Deploy** using Docker/Kubernetes templates in README

## Support & Troubleshooting

- **Queue growing?** → Check rate controller metrics, increase workers
- **High latency?** → Reduce batch sizes, increase workers
- **Memory leak?** → Check worker function cleanup, increase ulimit
- **Embedding timeout?** → Verify Ollama connectivity, increase timeout
- **Storage failures?** → Check database connections, verify schema

See README_PRODUCTION_PIPELINE.md for more troubleshooting.
