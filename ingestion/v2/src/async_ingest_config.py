"""Async ingestion configuration and chunk model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
import uuid


MAX_EMBED_CONCURRENCY = 2


@dataclass
class Chunk:
    text: str
    domain: str
    category: str
    embedding: List[float] = field(default_factory=list)
    source_book: str | None = None
    source_chapter: str | int | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_db_tuple(self) -> tuple:
        return (
            self.id,
            self.text,
            self.domain,
            self.category,
            self.embedding,
            self.source_book,
            self.source_chapter,
            self.metadata,
        )
