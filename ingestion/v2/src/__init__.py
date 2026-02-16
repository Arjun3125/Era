"""
RAG Ingestion Pipeline v2 - Async Multi-Stage Architecture

This package provides a production-ready async ingestion system with:
  - Adaptive rate limiting
  - Multi-stage pipeline (reader → embed → DB → aggregation)
  - Comprehensive metrics
  - 10-20x throughput improvement over sync

Main Entry Point:
  from ingestion.v2.src import main_ingest
  
  metrics = await main_ingest(
      book_paths=['book1.json', 'book2.json'],
      parse_func=my_parse_function,
      num_embed_workers=20
  )
"""

__version__ = "2.0.0"

# ============================================================================
# ASYNC PIPELINE - PRIMARY API (Recommended)
# ============================================================================

from .async_ingest_orchestrator import (
    AsyncIngestionPipeline,
    main_ingest,
)

from .async_ingest_config import (
    Chunk,
    MAX_EMBED_CONCURRENCY,
    EMBED_BATCH_SIZE,
    DB_BATCH_SIZE,
    MINISTER_BATCH_SIZE,
    QUEUE_MAXSIZE,
)

from .ingest_metrics import IngestMetrics

from .rate_controller import AdaptiveRateController

# ============================================================================
# ASYNC PIPELINE - WORKER EXPORTS (Advanced Usage)
# ============================================================================

from .async_workers import (
    reader_worker,
    embed_worker,
    db_bulk_writer,
    minister_aggregator,
)

# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # Main entry point
    "main_ingest",
    "AsyncIngestionPipeline",
    
    # Data models
    "Chunk",
    
    # Metrics & monitoring
    "IngestMetrics",
    
    # Rate limiting
    "AdaptiveRateController",
    
    # Configuration
    "MAX_EMBED_CONCURRENCY",
    "EMBED_BATCH_SIZE",
    "DB_BATCH_SIZE",
    "MINISTER_BATCH_SIZE",
    "QUEUE_MAXSIZE",
    
    # Workers (advanced)
    "reader_worker",
    "embed_worker",
    "db_bulk_writer",
    "minister_aggregator",
]
