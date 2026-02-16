"""Configuration and data models for async ingestion pipeline."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import uuid


# ============================================================================
# PIPELINE CONFIGURATION
# ============================================================================

MAX_EMBED_CONCURRENCY = 15
MAX_EMBED_CONCURRENCY_MIN = 2
MAX_EMBED_CONCURRENCY_MAX = 25

EMBED_BATCH_SIZE = 32
DB_BATCH_SIZE = 100
MINISTER_BATCH_SIZE = 50

QUEUE_MAXSIZE = 500

# Database connection pool
DB_POOL_MIN_SIZE = 3
DB_POOL_MAX_SIZE = 10

# Adaptive controller (conservative for stable GPU usage)
RATE_LIMIT_ADJUSTMENT_THRESHOLD = 10
LATENCY_WINDOW_SIZE = 60
LATENCY_LOWER_THRESHOLD = 0.5
LATENCY_UPPER_THRESHOLD = 1.5


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Chunk:
    """Represents a parsed chunk from a book."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    domain: str = "general"
    category: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list] = None
    source_book: Optional[str] = None
    source_chapter: Optional[int] = None

    def to_db_tuple(self):
        """Convert to tuple for DB bulk insert."""
        return (
            self.id,
            self.domain,
            self.category,
            self.text,
            self.embedding,
            self.source_book,
            self.source_chapter,
            1.0,  # weight
        )


__all__ = [
    "MAX_EMBED_CONCURRENCY",
    "MAX_EMBED_CONCURRENCY_MIN",
    "MAX_EMBED_CONCURRENCY_MAX",
    "EMBED_BATCH_SIZE",
    "DB_BATCH_SIZE",
    "MINISTER_BATCH_SIZE",
    "QUEUE_MAXSIZE",
    "DB_POOL_MIN_SIZE",
    "DB_POOL_MAX_SIZE",
    "RATE_LIMIT_ADJUSTMENT_THRESHOLD",
    "LATENCY_WINDOW_SIZE",
    "LATENCY_LOWER_THRESHOLD",
    "LATENCY_UPPER_THRESHOLD",
    "Chunk",
]
