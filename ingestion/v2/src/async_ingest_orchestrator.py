"""Async ingestion pipeline stub."""

from __future__ import annotations

import time
from typing import Any, Callable, List

try:  # pragma: no cover - allow both package and direct imports
    from .async_ingest_config import Chunk
    from .ingest_metrics import IngestMetrics
    from .ollama_client import OllamaClient
except ImportError:  # direct module import fallback
    from async_ingest_config import Chunk  # type: ignore
    from ingest_metrics import IngestMetrics  # type: ignore
    from ollama_client import OllamaClient  # type: ignore


class AsyncIngestionPipeline:
    def __init__(
        self,
        *,
        db_dsn: str | None = None,
        output_root: str = "data/ministers",
        llm_client: OllamaClient | None = None,
    ) -> None:
        self.db_dsn = db_dsn
        self.output_root = output_root
        self.llm_client = llm_client or OllamaClient()

    async def run(
        self,
        *,
        book_paths: List[str],
        parse_func: Callable[[str], List[Chunk]],
        num_embed_workers: int = 1,
    ) -> dict:
        metrics = IngestMetrics()
        start = time.time()
        chunks: List[Chunk] = []
        for path in book_paths:
            chunks.extend(parse_func(path))
        for chunk in chunks:
            embed_start = time.time()
            chunk.embedding = self.llm_client.embed(chunk.text)
            metrics.record_embed(time.time() - embed_start)
            metrics.record_processed(1)
        total_time = max(1e-6, time.time() - start)
        report = metrics.report()
        report["throughput_chunks_per_sec"] = report["processed_chunks"] / total_time
        report["avg_embed_latency_ms"] = report["avg_embed_latency_ms"]
        report["avg_db_latency_ms"] = report["avg_db_latency_ms"]
        report["errors"] = 0
        return report
