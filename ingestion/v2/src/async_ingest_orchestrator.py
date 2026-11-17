"""Async ingestion pipeline with bounded concurrency."""

from __future__ import annotations

import asyncio
import os
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

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class AsyncIngestionPipeline:
    def __init__(
        self,
        *,
        db_dsn: str | None = None,
        output_root: str = os.path.join(_PROJECT_ROOT, "data", "ministers"),
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

        if not chunks:
            total_time = max(1e-6, time.time() - start)
            report = metrics.report()
            report["throughput_chunks_per_sec"] = 0.0
            report["avg_embed_latency_ms"] = 0.0
            report["avg_db_latency_ms"] = 0.0
            report["errors"] = 0
            report["embeddings_created"] = []
            report["chunks_processed"] = 0
            return report

        semaphore = asyncio.Semaphore(max(1, int(num_embed_workers)))
        lock = asyncio.Lock()
        errors_count = 0

        async def _embed_chunk(chunk: Chunk) -> None:
            nonlocal errors_count
            async with semaphore:
                embed_start = time.time()
                try:
                    emb = await asyncio.to_thread(self.llm_client.embed, chunk.text)
                    chunk.embedding = emb
                    latency = time.time() - embed_start
                    async with lock:
                        metrics.record_embed(latency)
                        metrics.record_processed(1)
                except Exception:
                    async with lock:
                        errors_count += 1

        tasks = [_embed_chunk(chunk) for chunk in chunks]
        await asyncio.gather(*tasks)

        total_time = max(1e-6, time.time() - start)
        report = metrics.report()
        report["throughput_chunks_per_sec"] = report["processed_chunks"] / total_time
        report["avg_embed_latency_ms"] = report["avg_embed_latency_ms"]
        report["avg_db_latency_ms"] = report["avg_db_latency_ms"]
        report["errors"] = errors_count
        report["embeddings_created"] = [c.embedding for c in chunks if getattr(c, "embedding", None)]
        report["chunks_processed"] = len(chunks)
        return report

