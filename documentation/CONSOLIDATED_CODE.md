# CONSOLODIDATED PIPELINE SOURCE CODE

This file consolidates the key ingestion pipeline source modules for easier review.

---

## File: ingestion/v2/src/ingest_pipeline.py

```python
"""Main ingestion pipeline orchestrator."""
import json
import os
import sys
import shutil
from typing import Optional, List, Dict, Any

from .config import CHAPTER_TYPES
from .pdf_extraction import extract_pdf_pages, repair_glyph_text, looks_glyph_encoded
from .chapter_splitter import split_chapters_with_ollama_streaming, fallback_split_by_headings
from .doctrine_extractor import extract_doctrine
from .embeddings import normalize_doctrine, doctrine_to_nodes, embed_nodes
from .progress_tracker import live_progress
from .ollama_client import OllamaClient
from .utils import sha, chunk_text
from .minister_converter import convert_all_doctrines, update_combined_vector_index
from .capital_allocation import ingest_post_phase3
from .async_ingest_orchestrator import AsyncIngestionPipeline
from .async_ingest_config import Chunk, MAX_EMBED_CONCURRENCY
from .async_doctrine_workers import run_async_doctrine_extraction


def _is_ingest_completed(storage: str) -> bool:
    """Check if ingestion is already completed."""
    try:
        progress_path = os.path.join(storage, "progress.json")
        emb_path = os.path.join(storage, "03_embeddings.json")
        
        if os.path.exists(progress_path):
            with open(progress_path, "r", encoding="utf-8") as pf:
                prog = json.load(pf)
            if prog.get("current_phase") == "completed" or prog.get("phase") == "completed":
                return True
        
        if os.path.exists(emb_path):
            return True
    except Exception:
        pass
    return False


def _try_reconstruct_doctrine(chapter: Dict[str, Any], storage: str) -> Optional[Dict[str, Any]]:
    """Try to reconstruct doctrine from checkpointed chunk parses."""
    from .utils import sha
    
    try:
        doctrine_path = os.path.join(storage, "02_doctrine_chunks.json")
        if not os.path.exists(doctrine_path):
            return None
        
        with open(doctrine_path, "r", encoding="utf-8") as f:
            dstate = json.load(f)
        
        chapter_id = chapter.get("chapter_id") or sha(chapter.get("raw_text", ""))
        chapter_key = f"chapter_{chapter_id}"
        chap_state = dstate.get(chapter_key, {})
        completed = chap_state.get("completed", {})
        
        if not completed:
            return None
        
        # Aggregate available parsed chunks
        agg = {"domains": set(), "principles": [], "rules": [], "claims": [], "warnings": []}
        for idx in sorted(completed.keys(), key=lambda x: int(x)):
            parsed_chunk = completed.get(idx, {})
            for k in ("principles", "rules", "claims", "warnings"):
                agg[k].extend(parsed_chunk.get(k, []))
            for dname in parsed_chunk.get("domains", []):
                agg["domains"].add(dname)
        
        return {
            "chapter_index": chapter.get("chapter_index"),
            "chapter_title": chapter.get("chapter_title"),
            "domains": sorted(agg["domains"]),
            "principles": agg["principles"],
            "rules": agg["rules"],
            "claims": agg["claims"],
            "warnings": agg["warnings"],
        }
    except Exception:
        return None


def _enrich_doctrines(doctrines: List[Dict[str, Any]], chapters: List[Dict[str, Any]], storage: str):
    """Enrich doctrine objects with metadata."""
    from .utils import sha
    
    def classify_chapter(doctrine_obj, raw_text):
        """Classify chapter type based on content."""
        if any([
            doctrine_obj.get("principles"),
            doctrine_obj.get("rules"),
            doctrine_obj.get("claims"),
            doctrine_obj.get("warnings"),
        ]):
            return "doctrinal"

        text = (raw_text or "").lower()
        if len(raw_text or "") < 1500:
            return "introductory"

        narrative_markers = ["story", "example", "illustration", "history", "background", "context", "in this chapter"]
        if any(m in text for m in narrative_markers):
            return "narrative"

        return "commentary"

    def doctrine_density(d, raw_text):
        """Calculate doctrine density (items per word)."""
        count = (
            len(d.get("principles", []) or []) +
            len(d.get("rules", []) or []) +
            len(d.get("claims", []) or []) +
            len(d.get("warnings", []) or [])
        )
        return round(count / max(len((raw_text or "").split()), 1), 4)

    # Load chunk-level checkpoint state
    doctrine_chunks_path = os.path.join(storage, "02_doctrine_chunks.json")
    try:
        with open(doctrine_chunks_path, "r", encoding="utf-8") as f:
            chunks_state = json.load(f)
    except Exception:
        chunks_state = {}

    # Enrich each doctrine
    for idx, d in enumerate(doctrines, start=1):
        try:
            ch = chapters[idx - 1]
            raw_text = ch.get("raw_text", "") if isinstance(ch, dict) else ""
        except Exception:
            raw_text = ""

        # Compute extracted chunk count
        extracted_chunks = 0
        try:
            if isinstance(ch, dict):
                chapter_id = ch.get("chapter_id") or sha(ch.get("raw_text", ""))
                chapter_key = f"chapter_{chapter_id}"
                chap_state = chunks_state.get(chapter_key, {})
                extracted_chunks = len(chap_state.get("completed", {}) or {})
        except Exception:
            pass

        ctype = classify_chapter(d, raw_text)
        if ctype not in CHAPTER_TYPES:
            ctype = "commentary"

        density = doctrine_density(d, raw_text)
        status = d.get("_status") or ("valid_empty" if density == 0 else "ok")

        d["_meta"] = {
            "status": status,
            "chapter_type": ctype,
            "reason": ("No actionable doctrine present" if density == 0 else None),
            "doctrine_density": density,
            "extracted_chunks": extracted_chunks,
            "model_confidence": ("high" if density == 0 else "medium"),
        }


def build_minister_memories(
    doctrines: List[Dict[str, Any]],
    storage_root: str,
    client: OllamaClient,
    book_meta: Dict[str, Any],
    progress_cb: Optional[callable] = None,
    **kwargs,
) -> None:
    """
    Build minister memory artifacts from doctrines.
    
    Lightweight stub that writes minimal memory artifacts.
    In full system, this would create per-minister doctrine stores.
    
    Args:
        doctrines: List of extracted doctrines
        storage_root: Root storage directory
        client: OllamaClient instance
        book_meta: Book metadata dict
        progress_cb: Optional progress callback
    """
    os.makedirs(storage_root, exist_ok=True)
    if progress_cb:
        try:
            progress_cb(phase="phase_2.5", message="Building minister memories", current=1, total=1)
        except Exception:
            pass
    
    # Create trivial index file
    try:
        with open(os.path.join(storage_root, "ministers_index.json"), "w", encoding="utf-8") as f:
            json.dump({"book_meta": book_meta, "count": len(doctrines)}, f)
    except Exception:
        pass


def run_full_ingest_with_resume(pdf_path: str, resume: bool = True):
    """
    Main ingestion pipeline with resume support.
    
    Orchestrates all phases:
    - Phase 0: PDF extraction
    - Phase 0.5: Glyph repair
    - Phase 1: Chapter splitting
    - Phase 2: Doctrine extraction
    - Phase 2.5: Minister memories
    - Phase 3: Embeddings
    
    Args:
        pdf_path: Path to PDF file
        resume: If True, skip completed phases
    
    Raises:
        RuntimeError: If critical errors occur
    """
    book_id = os.path.splitext(os.path.basename(pdf_path))[0]
    storage = os.path.join("rag_storage", book_id)
    os.makedirs(storage, exist_ok=True)

    # Fast skip for already-completed books
    if resume:
        if _is_ingest_completed(storage):
            print(f"[INGEST] Skipping {book_id}: already completed", flush=True)
            return

    # Create clients
    extractor_client = OllamaClient()
    doctrine_client = OllamaClient()

    # ========== PHASE 0: PDF EXTRACTION ==========
    live_progress(storage, phase="phase_0", message="Starting PDF extraction")
    pages = extract_pdf_pages(pdf_path, storage=storage)
    raw = "\f".join(pages)

    # ========== PHASE 0.5: GLYPH REPAIR ==========
    repaired_path = os.path.join(storage, "00_raw_repaired.txt")
    if resume and os.path.exists(repaired_path):
        try:
            with open(repaired_path, "r", encoding="utf-8") as f:
                raw = f.read()
            live_progress(storage, phase="phase_0.5", message="Using cached repaired text (resume)")
        except Exception:
            pass
    else:
        if looks_glyph_encoded(raw):
            chunks = chunk_text(raw, max_chars=8000)
            repaired_chunks = []
            total_chunks = len(chunks)
            for ci, c in enumerate(chunks, start=1):
                live_progress(
                    storage,
                    phase="phase_0.5",
                    message="Repairing glyph text",
                    current=ci,
                    total=total_chunks,
                )
                try:
                    repaired_chunks.append(repair_glyph_text(c, client=extractor_client, storage=storage))
                except Exception:
                    repaired_chunks.append(c)

            raw = "\n\f\n".join(repaired_chunks)
            try:
                with open(repaired_path, "w", encoding="utf-8") as f:
                    f.write(raw)
            except Exception:
                pass
            live_progress(
                storage,
                phase="phase_0.5",
                message="Glyph repair completed",
                current=total_chunks,
                total=total_chunks,
            )

    # Persist canonical text
    canonical_path = os.path.join(storage, "00_canonical_text.txt")
    with open(os.path.join(storage, "00_raw.txt"), "w", encoding="utf-8") as f:
        f.write(raw)
    with open(canonical_path, "w", encoding="utf-8") as f:
        f.write(raw)
    live_progress(storage, phase="phase_0", message="PDF extraction completed")

    # ========== PHASE 1: CHAPTER SPLITTING ==========
    live_progress(storage, phase="phase_1", message="Chapter split (LLM) started")

    chapters_path = os.path.join(storage, "01_chapters.json")
    if resume and os.path.exists(chapters_path):
        with open(chapters_path, "r", encoding="utf-8") as f:
            chapters = json.load(f)
    else:
        chapters = split_chapters_with_ollama_streaming(
            pages,
            client=extractor_client,
            book_title=book_id,
            storage=storage,
        )
        
        # Fallback: try heading-based split if LLM returned single chapter
        if len(chapters) == 1:
            try:
                with open(canonical_path, "r", encoding="utf-8") as f:
                    canonical = f.read()
                fallback = fallback_split_by_headings(canonical)
                if len(fallback) > 1:
                    chapters = fallback
            except Exception:
                pass
        
        with open(chapters_path, "w", encoding="utf-8") as f:
            json.dump(chapters, f, indent=2, ensure_ascii=False)

    live_progress(
        storage,
        phase="phase_1",
        message="Chapter split (LLM) completed",
        current=len(chapters),
        total=len(chapters),
    )

    # ========== PHASE 2: DOCTRINE EXTRACTION (ASYNC) ==========
    live_progress(storage, phase="phase_2", message="Doctrine extraction started (async)")
    total = len(chapters)

    def phase2_progress(chapter_index, chunk_index, total_chunks):
        try:
            live_progress(
                storage,
                phase="phase_2",
                message=f"Extracting doctrine (chapter {chapter_index})",
                current=chunk_index,
                total=total_chunks,
            )
        except Exception:
            pass

    try:
        import asyncio
        
        # Run parallel doctrine extraction with 2 workers (avoids overwhelming Ollama)
        doctrines = asyncio.run(
            run_async_doctrine_extraction(
                chapters,
                client=doctrine_client,
                progress_cb=phase2_progress,
                storage=storage,
                num_workers=4,  # Increased for faster parallel extraction
            )
        )
        
        # Check for extraction errors
        errors = []
        for i, doc in enumerate(doctrines, start=1):
            if doc.get("_error"):
                errors.append(i)
                print(f"[PHASE 2] Chapter {i} extraction failed: {doc.get('_error')}")
        
        if len(errors) == total:
            raise RuntimeError("All chapters failed doctrine extraction — aborting")
        if errors:
            print(f"[INGEST] Completed with {len(errors)}/{total} extraction errors")
    
    except Exception as e:
        print(f"[INGEST][ERROR] Async doctrine extraction failed: {e}")
        # Fallback to sequential extraction
        print(f"[INGEST] Falling back to sequential extraction...")
        doctrines = []
        errors = []
        for i, ch in enumerate(chapters, start=1):
            live_progress(
                storage,
                phase="phase_2",
                message=f"Processing chapter {i}/{total} (fallback)",
                current=i - 1,
                total=total,
            )
            
            raw_len = len(ch.get("raw_text", "") if isinstance(ch, dict) else "")
            print(f"[PHASE 2] Chapter {i} index={ch.get('chapter_index')} raw_length={raw_len}")

            try:
                doc = extract_doctrine(
                    ch,
                    client=doctrine_client,
                    progress_cb=phase2_progress,
                    storage=storage,
                )
                doctrines.append(doc)
            except (ModuleNotFoundError, ImportError) as e2:
                raise RuntimeError(f"Critical import failure: {e2}") from e2
            except Exception as e2:
                # Try to recover from checkpoint
                reconstructed = _try_reconstruct_doctrine(ch, storage)
                if reconstructed:
                    doctrines.append(reconstructed)
                else:
                    errors.append(ch.get("chapter_index") or i)
                    doctrines.append({
                        "chapter_index": ch.get("chapter_index"),
                        "chapter_title": ch.get("chapter_title"),
                        "domains": [],
                        "principles": [],
                        "rules": [],
                        "claims": [],
                        "warnings": [],
                    })

    # Enrich doctrines with metadata
    _enrich_doctrines(doctrines, chapters, storage)

    # Sanity check
    for idx, d in enumerate(doctrines, start=1):
        if not isinstance(d, dict):
            raise RuntimeError(f"Doctrine object for chapter {idx} is not a dict: {type(d)}")

    # Write doctrines
    with open(os.path.join(storage, "02_doctrine.json"), "w", encoding="utf-8") as f:
        json.dump(doctrines, f, indent=2, ensure_ascii=False)

    # ========== PHASE 2.5: MINISTER MEMORIES ==========
    try:
        live_progress(storage, phase="phase_2.5", message="Building minister memories")
        ministers_storage = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "memory")
        )
        os.makedirs(ministers_storage, exist_ok=True)

        def _ministers_progress_cb(*, phase, message, current=None, total=None):
            try:
                live_progress(storage, phase=phase, message=message, current=current, total=total)
            except Exception:
                pass

        build_minister_memories(
            doctrines,
            storage_root=ministers_storage,
            client=doctrine_client,
            book_meta={"title": book_id},
            progress_cb=_ministers_progress_cb,
        )
        live_progress(storage, phase="phase_2.5", message="Minister memories built", current=1, total=1)
    except Exception as e:
        try:
            with open(os.path.join(storage, "02_doctrine_errors.log"), "a", encoding="utf-8") as ef:
                ef.write(f"Phase 2.5 error: {e}\n")
        except Exception:
            pass

    live_progress(storage, phase="phase_2", message="Doctrine extraction completed", current=total, total=total)

    # ========== PHASE 3: EMBEDDINGS (async pipeline) ==========
    live_progress(storage, phase="phase_3", message="Embedding started")
    nodes = []

    for d in doctrines:
        nd = normalize_doctrine(d)
        nodes.extend(doctrine_to_nodes(nd, prefix=book_id.upper()))

    nodes_to_embed = [n for n in nodes if n.get("type") in ("principle", "rule", "claim")]

    # Serialize chunks for the AsyncIngestionPipeline parser
    nodes_chunks_path = os.path.join(storage, "03_nodes_chunks.json")
    try:
        chunks_payload = []
        for n in nodes_to_embed:
            chunks_payload.append({
                "text": n.get("text", ""),
                "domain": n.get("metadata", {}).get("domain", "base"),
                "category": n.get("type", "content"),
                "source_book": book_id,
                "source_chapter": f"ch{n.get('metadata', {}).get('chapter', 0)}",
            })

        with open(nodes_chunks_path, 'w', encoding='utf-8') as nf:
            json.dump(chunks_payload, nf, indent=2, ensure_ascii=False)

        # Run the async ingestion pipeline to perform embeddings + DB writes
        try:
            import asyncio

            pipeline = AsyncIngestionPipeline(db_dsn=None, output_root=os.path.join(storage, 'ministers'), llm_client=extractor_client)
            metrics = asyncio.run(
                pipeline.run(
                    book_paths=[nodes_chunks_path],
                    parse_func=_parse_chunks_from_file,
                    num_embed_workers=MAX_EMBED_CONCURRENCY,
                )
            )

            # Persist a summary of embedding metrics
            try:
                with open(os.path.join(storage, "03_embeddings.json"), "w", encoding="utf-8") as f:
                    json.dump({"pipeline_metrics": metrics}, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        except Exception as e:
            # If async pipeline fails, fallback to synchronous embed_nodes
            print(f"[INGEST][WARN] Async pipeline failed - falling back to threaded embeddings: {e}")
```

---

## File: ingestion/v2/src/ingest_metrics.py

```python
"""Metrics collection and reporting for async ingestion pipeline."""
from collections import deque
from dataclasses import dataclass, field
from typing import Dict
import time


@dataclass
class IngestMetrics:
    """Collects and reports per-stage metrics."""
    
    embed_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    db_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    minister_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    processed: int = 0
    dropped: int = 0
    rate_limit_hits: int = 0
    errors: int = 0
    
    start_time: float = field(default_factory=time.time)
    last_report_time: float = field(default_factory=time.time)

    def record_embed(self, latency: float):
        """Record embedding call latency."""
        self.embed_times.append(latency)

    def record_db(self, latency: float):
        """Record DB write latency."""
        self.db_times.append(latency)

    def record_minister(self, latency: float):
        """Record minister aggregation latency."""
        self.minister_times.append(latency)

    def record_processed(self, count: int = 1):
        """Increment processed count."""
        self.processed += count

    def record_dropped(self, count: int = 1):
        """Increment dropped count."""
        self.dropped += count

    def record_rate_limit(self):
        """Increment rate limit hit counter."""
        self.rate_limit_hits += 1

    def record_error(self):
        """Increment error counter."""
        self.errors += 1

    def get_throughput(self) -> float:
        """Get throughput in chunks/sec."""
        elapsed = time.time() - self.start_time
        return self.processed / max(1, elapsed)

    def get_avg_embed_latency(self) -> float:
        """Get average embedding latency."""
        if not self.embed_times:
            return 0.0
        return sum(self.embed_times) / len(self.embed_times)

    def get_avg_db_latency(self) -> float:
        """Get average DB write latency."""
        if not self.db_times:
            return 0.0
        return sum(self.db_times) / len(self.db_times)

    def get_avg_minister_latency(self) -> float:
        """Get average minister aggregation latency."""
        if not self.minister_times:
            return 0.0
        return sum(self.minister_times) / len(self.minister_times)

    def report(self) -> Dict[str, float]:
        """Generate comprehensive metrics report."""
        elapsed = time.time() - self.start_time
        
        report = {
            "elapsed_seconds": elapsed,
            "processed_chunks": self.processed,
            "dropped_chunks": self.dropped,
            "rate_limit_hits": self.rate_limit_hits,
            "errors": self.errors,
            "throughput_chunks_per_sec": self.get_throughput(),
            "avg_embed_latency_ms": self.get_avg_embed_latency() * 1000,
            "avg_db_latency_ms": self.get_avg_db_latency() * 1000,
            "avg_minister_latency_ms": self.get_avg_minister_latency() * 1000,
        }
        
        self.last_report_time = time.time()
        return report

    @property
    def processed_chunks(self) -> int:
        """Compatibility alias for older code referencing processed_chunks."""
        return self.processed

    def print_report(self):
        """Print a formatted metrics report."""
        report = self.report()
        print("\n" + "=" * 70)
        print("INGESTION METRICS REPORT")
        print("=" * 70)
        for key, value in report.items():
            if isinstance(value, float):
                print(f"  {key:.<50} {value:.2f}")
            else:
                print(f"  {key:.<50} {value}")
        print("=" * 70 + "\n")


__all__ = ["IngestMetrics"]
```

---

## File: ingestion/v2/src/rate_controller.py

```python
"""Adaptive rate limiting controller for LLM embedding calls."""
import asyncio
from typing import Optional
from .async_ingest_config import (
    MAX_EMBED_CONCURRENCY,
    MAX_EMBED_CONCURRENCY_MIN,
    MAX_EMBED_CONCURRENCY_MAX,
    RATE_LIMIT_ADJUSTMENT_THRESHOLD,
    LATENCY_WINDOW_SIZE,
    LATENCY_LOWER_THRESHOLD,
    LATENCY_UPPER_THRESHOLD,
)


class AdaptiveRateController:
    """Dynamically adjusts concurrency and batch size based on API feedback."""

    def __init__(
        self,
        initial_concurrency: int = MAX_EMBED_CONCURRENCY,
        max_concurrency: int = MAX_EMBED_CONCURRENCY_MAX,
        min_concurrency: int = MAX_EMBED_CONCURRENCY_MIN,
    ):
        self.initial_concurrency = initial_concurrency
        self.concurrency = initial_concurrency
        self.max_concurrency = max_concurrency
        self.min_concurrency = min_concurrency

        self.success_count = 0
        self.rate_limit_hits = 0
        self.latencies = []
        
        # Semaphore for rate limiting
        self._semaphore = asyncio.Semaphore(self.concurrency)

    def record_success(self, latency: float):
        """Record a successful API call."""
        self.success_count += 1
        self.latencies.append(latency)

    def record_rate_limit(self):
        """Record a rate-limit error (429)."""
        self.rate_limit_hits += 1

    def record_error(self):
        """Record a generic error."""
        pass

    async def acquire(self):
        """Acquire a slot in the semaphore."""
        await self._semaphore.acquire()

    def release(self):
        """Release a semaphore slot."""
        self._semaphore.release()

    def adjust(self):
        """Adjust concurrency based on observed behavior."""
        
        # If we hit rate limits, back off aggressively
        if self.rate_limit_hits >= RATE_LIMIT_ADJUSTMENT_THRESHOLD:
            old_concurrency = self.concurrency
            self.concurrency = max(
                self.min_concurrency,
                int(self.concurrency * 0.7)
            )
            print(
                f"[RateController] Rate limit detected ({self.rate_limit_hits} hits). "
                f"Reduced concurrency: {old_concurrency} -> {self.concurrency}"
            )
            self.rate_limit_hits = 0
            self.latencies.clear()
            self._update_semaphore()
            return

        # If latencies are low, we can increase concurrency
        if len(self.latencies) >= LATENCY_WINDOW_SIZE:
            avg_latency = sum(self.latencies) / len(self.latencies)

            if avg_latency < LATENCY_LOWER_THRESHOLD:
                old_concurrency = self.concurrency
                self.concurrency = min(
                    self.max_concurrency,
                    self.concurrency + 2
                )
                print(
                    f"[RateController] Low latency ({avg_latency:.3f}s). "
                    f"Increased concurrency: {old_concurrency} -> {self.concurrency}"
                )
                self._update_semaphore()

            elif avg_latency > LATENCY_UPPER_THRESHOLD:
                old_concurrency = self.concurrency
                self.concurrency = max(
                    self.min_concurrency,
                    int(self.concurrency * 0.9)
                )
                print(
                    f"[RateController] High latency ({avg_latency:.3f}s). "
                    f"Reduced concurrency: {old_concurrency} -> {self.concurrency}"
                )
                self._update_semaphore()

            self.latencies.clear()

    def _update_semaphore(self):
        """Update the semaphore to reflect new concurrency limit."""
        # Create a new semaphore with updated capacity
        self._semaphore = asyncio.Semaphore(self.concurrency)

    async def sleep_backoff(self, attempt: int = 1):
        """Exponential backoff sleep (for rate limit recovery)."""
        await asyncio.sleep(min(2 ** attempt, 32))  # Cap at 32 seconds

    def get_status(self) -> dict:
        """Get current controller status."""
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        return {
            "current_concurrency": self.concurrency,
            "success_count": self.success_count,
            "rate_limit_hits": self.rate_limit_hits,
            "avg_latency": avg_latency,
            "latency_window": len(self.latencies),
        }


__all__ = ["AdaptiveRateController"]
```

---

## File: ingestion/v2/src/ollama_client.py

```python
"""Ollama LLM client wrapper."""
import json
import subprocess
from typing import List, Optional, Any, Dict
import os

from .config import DEFAULT_EXTRACT_MODEL, DEFAULT_DEEPSEEK_MODEL


class OllamaClient:
    """Minimal Ollama client that calls the `ollama` CLI.

    It provides `generate(prompt)` returning the model text output and
    `embed(text)` returning a numeric vector when supported by the CLI.
    """

    def __init__(self, model: Optional[str] = None, cmd: str = "ollama"):
        # Default to the extractor model unless explicitly provided
        self.model = model or DEFAULT_EXTRACT_MODEL
        self.cmd = cmd

    def _run(self, args: List[str], input_text: Optional[str] = None, timeout: int = 60) -> str:
        """
        Run ollama CLI command with proper encoding handling.
        
        Args:
            args: Command arguments
            input_text: Optional stdin text
            timeout: Command timeout in seconds
            
        Returns:
            Command stdout as string
            
        Raises:
            RuntimeError: If command fails
        """
        inp = input_text.encode("utf-8") if input_text is not None else None
        proc = subprocess.run(
            [self.cmd] + args,
            input=inp,
            capture_output=True,
            text=False,
            timeout=timeout,
        )
        out_b = proc.stdout or b""
        err_b = proc.stderr or b""
        
        try:
            out = out_b.decode("utf-8")
        except Exception:
            out = out_b.decode("utf-8", errors="replace")
        try:
            err = err_b.decode("utf-8")
        except Exception:
            err = err_b.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            raise RuntimeError(f"ollama command failed: {' '.join(args)}\nstdout={out}\nstderr={err}")

        return out

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: int = 60,
    ) -> str:
        """
        Generate text using ollama.
        
        Args:
            prompt: Input prompt
            model: Override model (optional)
            temperature: Model temperature (optional)
            timeout: Timeout in seconds
            
        Returns:
            Generated text
        """
        m = model or self.model
        args = ["run", m, prompt]
        return self._run(args, timeout=timeout).strip()

    def embed(self, text: str, model: Optional[str] = None, timeout: int = 60) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            model: Override model (optional)
            timeout: Timeout in seconds
            
        Returns:
            Embedding vector (768-d) or zero vector on failure
        """
        m = model or self.model
        try:
            out = self._run(["embed", m, "--text", text], timeout=timeout)
            try:
                vec = json.loads(out)
                if isinstance(vec, list):
                    return [float(x) for x in vec]
            except Exception:
                # fallback: attempt to extract JSON array substring
                start = out.find("[")
                end = out.rfind("]")
                if start != -1 and end != -1 and end > start:
                    try:
                        vec = json.loads(out[start:end + 1])
                        return [float(x) for x in vec]
                    except Exception:
                        pass
        except Exception:
            pass

        # Fallback: return a deterministic zero-vector
        return [0.0] * 768


def call_json_llm_strict(
    prompt: str,
    system: str,
    client: OllamaClient,
    timeout: int = 60,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call LLM and parse JSON object from output.

    Args:
        prompt: User prompt
        system: System prompt
        client: OllamaClient instance
        timeout: Timeout in seconds
        model: Override model selection
        
    Returns:
        Parsed JSON object or safe fallback
    """
    full = (system or "") + "\n\n" + prompt
    
    # Choose model: explicit override, or deepseek if doctrine-related
    selected_model = model
    if selected_model is None:
        low = (system or "").lower()
        if "doctrine" in low or "deepseek" in low or "doctrine extraction" in low:
            selected_model = DEFAULT_DEEPSEEK_MODEL
        else:
            selected_model = client.model or DEFAULT_EXTRACT_MODEL

    raw = client.generate(full, model=selected_model, timeout=timeout)
    if not raw:
        return {}

    # Try parse entire output
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to extract first JSON object substring
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            if isinstance(obj, dict):
                # ensure required doctrine keys are present
                for k in ("domains", "principles", "rules", "claims", "warnings"):
                    if k not in obj:
                        obj[k] = []
                return obj
        except Exception:
            pass

    # Safe deterministic fallbacks
    lower = (system or "").lower() + "\n" + (prompt or "").lower()
    if "decision" in lower:
        return {"decision": "continue_chapter", "confidence": 0.0}
    if "domains" in lower:
        # minimal abstracted doctrine (non-empty) as safe default
        return {
            "domains": ["strategy"],
            "principles": [{"statement": "Prioritize clear objectives", "abstracted_from": None}],
            "rules": [{"condition": "When uncertain", "action": "Prefer conservative options"}],
            "claims": [],
            "warnings": [],
        }

    return {}
```

---

## File: ingestion/v2/src/doctrine_extractor.py

```python
"""Doctrine extraction and validation logic."""
import json
import os
from typing import Dict, Any, List, Optional, Callable

from .config import ALLOWED_DOMAINS, SYSTEM_PROMPT_DOCTRINE
from .utils import sha, chunk_text, dedupe_list, infer_domains_from_text
from .ollama_client import OllamaClient, call_json_llm_strict


# ============================================================
# Validation Functions
# ============================================================

REQUIRED_DOCTRINE_KEYS = {
    "domains",
    "principles",
    "rules",
    "claims",
    "warnings",
}


def validate_doctrine_inline(doc: dict, *, context: str) -> dict:
    """
    Inline doctrine validation. Hard fail if structure invalid.
    
    Args:
        doc: Doctrine object to validate
        context: Context string for error messages
        
    Returns:
        Validated doc
        
    Raises:
        RuntimeError: If validation fails
    """
    if not isinstance(doc, dict):
        raise RuntimeError(f"[DOCTRINE][{context}] Output is not a dict: {type(doc)}")

    for key in REQUIRED_DOCTRINE_KEYS:
        if key not in doc:
            raise RuntimeError(f"[DOCTRINE][{context}] Missing key: {key}")
        if not isinstance(doc[key], list):
            raise RuntimeError(f"[DOCTRINE][{context}] Key '{key}' is not a list")

    return doc


def reject_verbatim_quotes_inline(
    doc: dict,
    raw_text: str,
    *,
    context: str,
    min_words: int = 12,
) -> None:
    """
    Detect verbatim quoted spans from source text.
    Raises if detected (abstraction requirement).
    
    Args:
        doc: Doctrine object
        raw_text: Original source text
        context: Context string for error messages
        min_words: Minimum contiguous words to flag as verbatim
        
    Raises:
        RuntimeError: If verbatim quote detected
    """
    import re
    
    if not raw_text:
        return

    raw_norm = re.sub(r"\s+", " ", raw_text).lower()
    raw_words = raw_norm.split()
    n_raw = len(raw_words)
    raw_ngrams = set()
    max_n = min(20, n_raw)
    for n in range(min_words, max_n + 1):
        for i in range(0, n_raw - n + 1):
            raw_ngrams.add(" ".join(raw_words[i:i + n]))

    def extract_texts_from_doc(d: dict) -> list:
        outs = []
        for p in d.get("principles", []) or []:
            if isinstance(p, dict):
                outs.append(str(p.get("statement", "")))
            else:
                outs.append(str(p))
        for r in d.get("rules", []) or []:
            if isinstance(r, dict):
                cond = r.get("condition", "")
                act = r.get("action", "")
                outs.append(f"{cond} {act}".strip())
            else:
                outs.append(str(r))
        for c in d.get("claims", []) or []:
            if isinstance(c, dict):
                outs.append(str(c.get("claim", "")))
            else:
                outs.append(str(c))
        for w in d.get("warnings", []) or []:
            if isinstance(w, dict):
                outs.append(f"{w.get('situation','')} {w.get('risk','')".strip())
            else:
                outs.append(str(w))
        return [re.sub(r"\s+", " ", t).lower() for t in outs if t and isinstance(t, str)]

    texts = extract_texts_from_doc(doc)
    for t in texts:
        words = t.split()
        L = len(words)
        if L < min_words:
            continue
        max_check = min(20, L)
        for n in range(min_words, max_check + 1):
            for i in range(0, L - n + 1):
                phrase = " ".join(words[i:i + n])
                if phrase in raw_ngrams:
                    raise RuntimeError(
                        f"[DOCTRINE][{context}] Verbatim phrase detected: '{phrase[:80]}...'"
                    )


# ============================================================
# Doctrine Extraction
# ============================================================

def extract_doctrine(
    chapter: Dict[str, Any],
    *,
    client: OllamaClient,
    progress_cb: Optional[Callable] = None,
    storage: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract abstracted doctrine from a chapter using LLM.
    
    Phase 2: Processes chapter into chunks, extracts doctrine via LLM,
    validates structure and content, and aggregates results.
    
    Args:
        chapter: Chapter dict with 'chapter_index', 'raw_text', etc.
        client: OllamaClient instance
        progress_cb: Optional progress callback(chapter_index, chunk_index, total_chunks)
        storage: Optional storage directory for checkpoints
        
    Returns:
        Doctrine dict with domains, principles, rules, claims, warnings
        
    Raises:
        RuntimeError: If extraction fails critically
    """
    chapter_index = chapter["chapter_index"]
    chapter_title = chapter.get("chapter_title")
    chapter_id = chapter.get("chapter_id") or sha(chapter.get("raw_text", ""))

    text = chapter.get("raw_text", "")
    chunks = chunk_text(text, max_chars=8000)
    total_chunks = len(chunks)
    print(f"[DOCTRINE] Chapter {chapter_index} total_chunks={total_chunks}")

    if not chunks:
        raise RuntimeError(f"Phase 2 failed at chapter {chapter_index}: empty text")

    aggregated = {
        "domains": set(),
        "principles": [],
        "rules": [],
        "claims": [],
        "warnings": [],
    }

    # Load checkpoint state for resume support
    doctrine_path = os.path.join(storage, "02_doctrine_chunks.json") if storage else None
    if doctrine_path and os.path.exists(doctrine_path):
        try:
            with open(doctrine_path, "r", encoding="utf-8") as f:
                doctrine_state = json.load(f)
        except Exception:
            doctrine_state = {}
    else:
        doctrine_state = {}

    chapter_key = f"chapter_{chapter_id}"
    chapter_state = doctrine_state.get(chapter_key, {"total_chunks": total_chunks, "completed": {}})

    # Check if already completed
    completed = chapter_state.get("completed", {})
    if len(completed) == total_chunks and total_chunks > 0:
        print(f"[PHASE 2] Chapter {chapter_index} already completed — skipping")
        # Reconstruct from completed chunks
        for i in range(total_chunks):
            parsed_chunk = completed.get(str(i), {})
            aggregated["principles"].extend(parsed_chunk.get("principles", []))
            aggregated["rules"].extend(parsed_chunk.get("rules", []))
            aggregated["claims"].extend(parsed_chunk.get("claims", []))
            aggregated["warnings"].extend(parsed_chunk.get("warnings", []))
            for d in parsed_chunk.get("domains", []):
                aggregated["domains"].add(d)
    else:
        # Process chunks
        for i, chunk in enumerate(chunks):
            if progress_cb:
                try:
                    progress_cb(
                        chapter_index=chapter_index,
                        chunk_index=i + 1,
                        total_chunks=total_chunks,
                    )
                except Exception:
                    pass

            print(f"[DOCTRINE] Chapter {chapter_index} Chunk {i+1}/{total_chunks} ({len(chunk)} chars)")

            idx = str(i)
            if idx in chapter_state.get("completed", {}):
                parsed = chapter_state["completed"][idx]
            else:
                parsed = _extract_chunk_doctrine(
                    chunk,
                    chapter_index,
                    i,
                    client,
                    storage,
                )

                # Checkpoint
                chapter_state.setdefault("completed", {})[idx] = {
                    "domains": parsed.get("domains", []),
                    "principles": parsed.get("principles", []),
                    "rules": parsed.get("rules", []),
                    "claims": parsed.get("claims", []),
                    "warnings": parsed.get("warnings", []),
                    **({"_verbatim_warning": parsed.get("_verbatim_warning")} if parsed.get("_verbatim_warning") else {}),
                }
                doctrine_state[chapter_key] = chapter_state
                if doctrine_path:
                    try:
                        with open(doctrine_path, "w", encoding="utf-8") as f:
                            json.dump(doctrine_state, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass

            # Aggregate
            for k in ("principles", "rules", "claims", "warnings"):
                aggregated[k].extend(parsed.get(k, []))
            for d in parsed.get("domains", []):
                aggregated["domains"].add(d)

    # Deduplicate and construct result
    for k in ("principles", "rules", "claims", "warnings"):
        aggregated[k] = dedupe_list(aggregated[k])

    result = {
        "chapter_index": chapter_index,
        "chapter_title": chapter_title,
        "domains": sorted(aggregated["domains"]),
        "principles": aggregated["principles"],
        "rules": aggregated["rules"],
        "claims": aggregated["claims"],
        "warnings": aggregated["warnings"],
    }

    # Validate structure
    if not _is_doctrine_structurally_valid(result):
        err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
        try:
            with open(err_path, "a", encoding="utf-8") as ef:
                ef.write(f"[ERROR] Invalid schema for chapter {chapter_index}\n")
        except Exception:
            pass
        raise RuntimeError(f"[DOCTRINE] Invalid schema for chapter {chapter_index}")

    # Check for actionable content
    if not _has_actionable_doctrine(result):
        print(f"[DOCTRINE] Chapter {chapter_index}: no actionable doctrine (valid_empty)")
        result["_status"] = "valid_empty"

    print(
        f"[DOCTRINE] Extracted {len(result.get('principles', []))} principles, "
        f"{len(result.get('rules', []))} rules, {len(result.get('claims', []))} claims, "
        f"{len(result.get('warnings', []))} warnings for chapter {chapter_index}"
    )

    return result


def _extract_chunk_doctrine(
    chunk: str,
    chapter_index: int,
    chunk_idx: int,
    client: OllamaClient,
    storage: Optional[str],
) -> Dict[str, Any]:
    """
    Extract doctrine from a single text chunk with retry logic.
    
    Args:
        chunk: Text chunk to process
        chapter_index: Chapter number for logging
        chunk_idx: Chunk index for logging
        client: OllamaClient instance
        storage: Storage directory for error logs
        
    Returns:
        Parsed doctrine object
        
    Raises:
        RuntimeError: If extraction fails after retries
    """
    user_prompt = f"""
RETURN JSON WITH THIS EXACT STRUCTURE:

{
    "domains": [],
    "principles": [],
    "rules": [],
    "claims": [],
    "warnings": []
}

CHAPTER INDEX: {chapter_index}

TEXT (for analysis only — DO NOT QUOTE):
--------------------------------------
{chunk[:8000]}
--------------------------------------

INSTRUCTIONS:
1. First, select 1–3 applicable DOMAINS from the allowed list.
2. Then extract abstracted doctrine ONLY within those domains.
3. Use normalized, decision-oriented language.
4. Do not quote the text.

REMEMBER:
- domains is REQUIRED
- domains must NOT be empty
"""

    user_prompt_retry = user_prompt + """
RETRY MODE:
- Paraphrase aggressively
- Reduce sentence length
- Prefer generalized verbs
"""

    parsed = None
    last_err = None
    
    for attempt in (1, 2):
        try:
            prompt_to_use = user_prompt if attempt == 1 else user_prompt_retry
            parsed = call_json_llm_strict(
                prompt=prompt_to_use,
                system=SYSTEM_PROMPT_DOCTRINE,
                client=client,
                timeout=180,
            )

            if not isinstance(parsed, dict):
                raise ValueError("Parsed chunk is not a JSON object")

            # Ensure domains
            if not parsed.get("domains"):
                parsed["domains"] = infer_domains_from_text(chunk)
                err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
                try:
                    with open(err_path, "a", encoding="utf-8") as ef:
                        ef.write(
                            f"Chapter {chapter_index}, chunk {chunk_idx+1}: "
                            f"domains missing; inferred {parsed['domains']}\n"
                        )
                except Exception:
                    pass

            # Validate
            validate_doctrine_inline(parsed, context=f"chapter={chapter_index},chunk={chunk_idx+1}")
            try:
                reject_verbatim_quotes_inline(parsed, chunk, context=f"chapter={chapter_index},chunk={chunk_idx+1}")
            except RuntimeError as rv_err:
                parsed["_verbatim_warning"] = str(rv_err)

            last_err = None
            break
        except Exception as e:
            last_err = e
            err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
            try:
                with open(err_path, "a", encoding="utf-8") as ef:
                    ef.write(f"Chapter {chapter_index} chunk {chunk_idx+1} attempt {attempt} error: {e}\n")
            except Exception:
                pass
            parsed = None

    if parsed is None:
        raise RuntimeError(
            f"Doctrine extraction failed: chapter={chapter_index} chunk={chunk_idx+1}: {last_err}"
        ) from last_err

    return parsed


def _is_doctrine_structurally_valid(d: Dict[str, Any]) -> bool:
    """Check if doctrine has required structure."""
    return (
        isinstance(d, dict)
        and "domains" in d
        and "principles" in d
        and "rules" in d
        and "claims" in d
        and "warnings" in d
    )


def _has_actionable_doctrine(d: Dict[str, Any]) -> bool:
    """Check if doctrine contains any actionable content."""
    return any([
        len(d.get("principles", [])) > 0,
        len(d.get("rules", [])) > 0,
        len(d.get("claims", [])) > 0,
        len(d.get("warnings", [])) > 0,
    ])
```

---

## File: ingestion/v2/src/async_doctrine_workers.py

```python
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
            # Get chapter with timeout
            chapter = await asyncio.wait_for(chapter_queue.get(), timeout=5.0)
            
            # Check for sentinel (None) to exit
            if chapter is None:
                chapter_queue.task_done()
                break
            
            # Acquire rate control slot (throttles if Ollama is slow)
            await rate_controller.acquire()
            
            chapter_index = chapter.get("chapter_index", "?")
            logger.info(f"[Doctrine Worker {worker_id}] Starting chapter {chapter_index}")
            
            try:
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
                
            except Exception as e:
                logger.error(f"[Doctrine Worker {worker_id}] Failed chapter {chapter_index}: {e}")
                metrics.record_error()
                # Put error marker
                await result_queue.put((chapter_index, {"_error": str(e)}))
            
            finally:
                chapter_queue.task_done()
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
    num_workers: int = 2,
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
    
    return doctrines
```

---

## File: ingestion/v2/src/async_workers.py

```python
(See full file in project: ingestion/v2/src/async_workers.py)

# This module implements: reader_worker, embed_worker, embed_batch,
# db_bulk_writer, _bulk_insert_postgres, _bulk_insert_stub, minister_aggregator,
# _flush_domain, _flush_all_domains.

# The file is included verbatim in the project; reference the source for details.
```

---

## File: ingestion/v2/src/vector_db.py

```python
"""Vector DB schema and helper functions for combined and per-domain embeddings.

Provides SQL schema strings for Postgres + pgvector and a file-backed stub
implementation for local testing and retrieval.
"""
import json
import os
import uuid
from typing import List, Dict, Any, Optional

COMBINED_SCHEMA = """
CREATE TABLE IF NOT EXISTS minister_embeddings (
    id UUID PRIMARY KEY,
    domain VARCHAR(50),
    category VARCHAR(50),
    text TEXT,
    embedding VECTOR(1536),
    source_book VARCHAR(255),
    source_chapter INT,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS minister_embeddings_idx ON minister_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 200);
"""

DOMAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS minister_domain_embeddings (
    id UUID PRIMARY KEY,
    domain VARCHAR(50),
    category VARCHAR(50),
    text TEXT,
    embedding VECTOR(1536),
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS minister_domain_embeddings_idx ON minister_domain_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
"""

VALID_DOMAINS = [
    "adaptation",
    "base",
    "conflict",
    "constraints",
    "data",
    "diplomacy",
    "discipline",
    "executor",
    "legitimacy",
    "optionality",
    "power",
    "psychology",
    "registry",
    "risk",
    "strategy",
    "technology",
    "timing",
    "truth",
    "key_constr",
]


class VectorDBStub:
    """File-backed stub for storing embeddings and performing naive searches."""

    def __init__(self, storage_root: str = "data"):
        self.storage_root = storage_root
        self.path = os.path.join(self.storage_root, "vector_db_stub.json")
        os.makedirs(self.storage_root, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"combined": {}, "domain": {}}, f, indent=2)

    def _read(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def insert_combined(self, domain: str, category: str, text: str, embedding: List[float], source_book: Optional[str] = None, source_chapter: Optional[int] = None, weight: float = 1.0) -> str:
        assert domain in VALID_DOMAINS, f"Invalid domain: {domain}"
        data = self._read()
        eid = str(uuid.uuid4())
        data["combined"][eid] = {
            "id": eid,
            "domain": domain,
            "category": category,
            "text": text,
            "embedding": embedding,
            "source_book": source_book,
            "source_chapter": source_chapter,
            "weight": weight,
        }
        self._write(data)
        return eid

    def insert_domain(self, domain: str, category: str, text: str, embedding: List[float], weight: float = 1.0) -> str:
        assert domain in VALID_DOMAINS, f"Invalid domain: {domain}"
        data = self._read()
        eid = str(uuid.uuid4())
        domain_map = data.setdefault("domain", {}).setdefault(domain, {})
        domain_map[eid] = {
            "id": eid,
            "domain": domain,
            "category": category,
            "text": text,
            "embedding": embedding,
            "weight": weight,
        }
        self._write(data)
        return eid

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        # simple dot / norms
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    def search_domain(self, domain: str, query_embedding: List[float], topk: int = 10) -> List[Dict[str, Any]]:
        assert domain in VALID_DOMAINS, f"Invalid domain: {domain}"
        data = self._read()
        items = list(data.get("domain", {}).get(domain, {}).values())
        scored = []
        for it in items:
            sim = self._cosine(query_embedding, it.get("embedding", []))
            scored.append((sim * (it.get("weight", 1.0) or 1.0), it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:topk]]

    def search_combined(self, query_embedding: List[float], topk: int = 10) -> List[Dict[str, Any]]:
        data = self._read()
        items = list(data.get("combined", {}).values())
        scored = []
        for it in items:
            sim = self._cosine(query_embedding, it.get("embedding", []))
            scored.append((sim * (it.get("weight", 1.0) or 1.0), it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:topk]]


def validate_domain(domain: str):
    if domain not in VALID_DOMAINS:
        raise ValueError(f"Domain '{domain}' is not in VALID_DOMAINS")


__all__ = ["COMBINED_SCHEMA", "DOMAIN_SCHEMA", "VectorDBStub", "VALID_DOMAINS", "validate_domain"]
```

---

## File: ingestion/v2/src/config.py

```python
"""Configuration and constants for the ingestion pipeline."""
import os

# ============================================================
# Model Configuration
# ============================================================
DEFAULT_EXTRACT_MODEL = os.environ.get("OLLAMA_EXTRACT_MODEL", "qwen2.5-coder:latest")
DEFAULT_DEEPSEEK_MODEL = os.environ.get("OLLAMA_DEEPSEEK_MODEL", "huihui_ai/deepseek-r1-abliterated:8b")

# ============================================================
# Processing Parameters
# ============================================================
MAX_WORKERS = 4  # Thread pool size for parallel processing
MAX_TOKENS = 2000
MAX_CHARS = int(MAX_TOKENS * 3.5)  # ~7000 chars per chunk

# ============================================================
# Cache Configuration
# ============================================================
CACHE_DIR = os.path.join("rag_cache", "llm")
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================
# Doctrine Domain Configuration
# ============================================================
ALLOWED_DOMAINS = [
    "adaptation",
    "base",
    "conflict",
    "constraints",
    "data",
    "diplomacy",
    "discipline",
    "executor",
    "legitimacy",
    "optionality",
    "power",
    "psychology",
    "registry",
    "risk",
    "strategy",
    "technology",
    "timing",
    "truth",
]

DOMAIN_KEYWORDS = {
    "adaptation": ["adapt", "adaptation", "adaptable"],
    "base": ["base", "ground", "position"],
    "conflict": ["conflict", "fight", "battle", "combat"],
    "constraints": ["limit", "constraint", "constraint"],
    "data": ["intelligence", "data", "information", "intel"],
    "diplomacy": ["diplomacy", "negotiat", "treaty"],
    "discipline": ["discipline", "order", "training"],
    "executor": ["execute", "executor", "implement"],
    "legitimacy": ["legitimacy", "legitimize", "authority"],
    "optionality": ["option", "optional", "choices"],
    "power": ["power", "force", "strength", "army"],
    "psychology": ["moral", "morale", "psych", "fear", "confidence"],
    "registry": ["register", "record", "registry"],
    "risk": ["risk", "danger", "hazard", "loss"],
    "strategy": ["strategy", "strategic", "plan", "planning"],
    "technology": ["technology", "tech", "weapon", "armament"],
    "timing": ["time", "timing", "tempo", "speed"],
    "truth": ["truth", "fact", "verify", "verify"],
}

CHAPTER_TYPES = {
    "doctrinal",
    "narrative",
    "historical",
    "introductory",
    "transitional",
    "commentary",
    "appendix",
    "summary",
}

# ============================================================
# Prompt Templates
# ============================================================
PHASE1_SYSTEM_PROMPT = """
You are a deterministic book-structure parser.

Your ONLY task is to detect chapter boundaries.

You will receive text incrementally.
You must decide ONE of the following exact values:

- start_new_chapter
- continue_chapter
- end_chapter

STRICT OUTPUT REQUIREMENTS (READ CAREFULLY):
- You MUST return ONLY a single JSON object and NOTHING else (no commentary,
    no markdown, no explanation, no code fences).
- The JSON object MUST exactly match this structure:
    {"decision": "start_new_chapter" | "continue_chapter" | "end_chapter", "confidence": 0.0}
- Use the lowercase decision strings shown above exactly.
- Set "confidence" to a float between 0.0 and 1.0. If unsure, return 0.0.
- If you cannot follow these rules, return {"decision": "continue_chapter", "confidence": 0.0}.

RULES:
- Do NOT summarize, interpret, or invent content.
- Do NOT quote or copy large verbatim passages.
- Do NOT reorder text.
- Be deterministic: prefer conservative choices when uncertain.

Return ONLY valid JSON.
"""

SYSTEM_PROMPT_DOCTRINE = f"""
You are a doctrine extraction engine.

Your task is NOT to quote the book.
Your task is to ABSTRACT operational doctrine.

MANDATORY OUTPUT REQUIREMENTS:
- You MUST include a field called "domains".
- "domains" MUST be a list of 1 to 3 items.
- Each domain MUST be chosen ONLY from the list below.
- If no domain applies, choose the closest applicable domain.

ALLOWED DOMAINS (EXACT STRINGS):
{', '.join(ALLOWED_DOMAINS)}

STRICT RULES:
- DO NOT copy sentences from the text.
- DO NOT quote phrases longer than 5 consecutive words.
- DO NOT use literary or rhetorical language.
- ALL outputs must be generalized, normalized, and actionable.

Return ONLY valid JSON matching the schema.
"""
```

---

*End of consolidated selection.*

If you want every single source file included (the project contains additional helpers, tests, and scripts), I can append them — tell me if you want the remaining modules included too.
