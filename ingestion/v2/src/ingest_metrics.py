"""Metrics collection for ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class IngestMetrics:
    embed_latencies: List[float] = field(default_factory=list)
    db_latencies: List[float] = field(default_factory=list)
    processed_chunks: int = 0

    def record_embed(self, latency: float) -> None:
        self.embed_latencies.append(float(latency))

    def record_db(self, latency: float) -> None:
        self.db_latencies.append(float(latency))

    def record_processed(self, count: int) -> None:
        self.processed_chunks += int(count)

    def report(self) -> dict:
        avg_embed = sum(self.embed_latencies) / len(self.embed_latencies) if self.embed_latencies else 0.0
        avg_db = sum(self.db_latencies) / len(self.db_latencies) if self.db_latencies else 0.0
        return {
            "processed_chunks": self.processed_chunks,
            "avg_embed_latency_ms": avg_embed * 1000.0,
            "avg_db_latency_ms": avg_db * 1000.0,
        }
