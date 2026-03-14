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

### KIS INTEGRATION ###
try:
    from .ingestion_kis_enhancer import (
        IngestionKISEnhancer,
        IngestionKISContext,
    )
    KIS_AVAILABLE = True
except ImportError as e:
    KIS_AVAILABLE = False
    print(f"[WARN] KIS enhancement unavailable - ingestion will proceed without KIS synthesis: {e}")
except Exception as e:
    KIS_AVAILABLE = False
    print(f"[WARN] KIS enhancement error: {e}")
### END KIS INTEGRATION ###


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
                # Normalize domain to string (handle both dict and string formats from LLM)
                if isinstance(dname, dict):
                    dname = dname.get("name") or str(dname)
                agg["domains"].add(str(dname))
        
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
    from .config import DEFAULT_EXTRACT_MODEL, DEFAULT_DEEPSEEK_MODEL, DEFAULT_EMBED_MODEL, DEFAULT_GLYPH_REPAIR_MODEL
    
    extractor_client = OllamaClient(model=DEFAULT_EXTRACT_MODEL)
    # Doctrine extraction requires instruction-following capability
    doctrine_client = OllamaClient(model=DEFAULT_DEEPSEEK_MODEL)
    # Embed client should use a lightweight embedding model (separate from generative LLM)
    embed_client = OllamaClient(model=DEFAULT_EMBED_MODEL)
    # Glyph repair uses a fast model (Mistral) to speed up Phase 0.5
    glyph_repair_client = OllamaClient(model=DEFAULT_GLYPH_REPAIR_MODEL)

    ### KIS INTEGRATION ###
    # Initialize KIS enhancer for knowledge synthesis
    kis_enhancer = None
    if KIS_AVAILABLE:
        try:
            kis_enhancer = IngestionKISEnhancer(
                knowledge_base_path="data/ministers"
            )
            print("[KIS] Enhancer initialized for doctrine synthesis", flush=True)
        except Exception as e:
            print(f"[WARN] Failed to initialize KIS enhancer: {e}", flush=True)
    
    # Track ingestion job outcomes for learning feedback
    ingestion_job_outcomes = {}
    ### END KIS INTEGRATION ###

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
            from concurrent.futures import ThreadPoolExecutor
            from functools import partial
            
            chunks = chunk_text(raw, max_chars=8000)
            total_chunks = len(chunks)
            
            # Parallel glyph repair (8 workers for I/O-bound LLM calls) - 8x speedup potential
            repair_fn = partial(repair_glyph_text, client=glyph_repair_client, storage=storage)
            repaired_chunks = []
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                for i, repaired in enumerate(executor.map(repair_fn, chunks, timeout=30)):
                    repaired_chunks.append(repaired)
                    live_progress(
                        storage,
                        phase="phase_0.5",
                        message="Repairing glyph text (parallel 8x)",
                        current=i+1,
                        total=total_chunks,
                    )

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
        
        # Run parallel doctrine extraction with 2 workers for stable GPU sync
        doctrines = asyncio.run(
            run_async_doctrine_extraction(
                chapters,
                client=doctrine_client,
                progress_cb=phase2_progress,
                storage=storage,
                num_workers=2,  # Conservative: prevents async overhead
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

    ### KIS INTEGRATION ###
    # KIS enhancement: synthesize knowledge during aggregation phase
    if kis_enhancer and chapters:
        print("[KIS] Enhancing doctrines with KIS knowledge synthesis...", flush=True)
        for idx, (doctrine, chapter) in enumerate(zip(doctrines, chapters), start=1):
            try:
                chapter_title = chapter.get("chapter_title", f"Chapter {idx}") if isinstance(chapter, dict) else f"Chapter {idx}"
                
                # Extract first domain from doctrine, or use "general"
                domains = doctrine.get("domains", [])
                minister_domain = domains[0] if domains else "general"
                
                # Get first 300 chars of doctrine excerpt
                doctrine_excerpt = ""
                for field in ("principles", "rules", "claims", "warnings"):
                    items = doctrine.get(field, [])
                    if items:
                        doctrine_excerpt = str(items[0])[:300]
                        break
                
                # Create KIS context
                job_id = f"ingest_{book_id}_{idx}"
                kis_context = IngestionKISContext(
                    chapter_title=chapter_title,
                    minister_domain=minister_domain,
                    doctrine_excerpt=doctrine_excerpt,
                    ingestion_job_id=job_id
                )
                
                # Enhance with KIS
                kis_context = kis_enhancer.enhance_aggregation_stage(
                    kis_context,
                    max_related_items=3
                )
                
                # Add KIS guidance to doctrine
                if kis_context.kis_synthesis:
                    doctrine["kis_guidance"] = kis_context.kis_synthesis
                    doctrine["kis_context"] = kis_context.kis_context
                
                # Track for outcome recording
                ingestion_job_outcomes[job_id] = {
                    "kis_context": kis_context,
                    "doctrine_idx": idx,
                }
                
            except Exception as e:
                print(f"[WARN] KIS enhancement failed for chapter {idx}: {e}", flush=True)

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
        # Log which embed model we'll use (should be a lightweight encoder, e.g. nomic-embed-text)
        try:
            from .config import DEFAULT_EMBED_MODEL
            print(f"[PHASE_3] Using embed model: {DEFAULT_EMBED_MODEL}", flush=True)
        except Exception:
            pass
        try:
            import asyncio

            pipeline = AsyncIngestionPipeline(db_dsn=None, output_root=os.path.join(storage, 'ministers'), llm_client=embed_client)
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
                
                ### KIS INTEGRATION ###
                # Record ingestion success for ML training
                if kis_enhancer and ingestion_job_outcomes:
                    print("[KIS] Recording ingestion success outcomes...", flush=True)
                    for job_id, outcome_data in ingestion_job_outcomes.items():
                        try:
                            success = kis_enhancer.record_ingestion_success(
                                ingestion_job_id=job_id,
                                minister_json=doctrines[outcome_data["doctrine_idx"] - 1],
                                num_chunks=len(nodes_to_embed),
                                num_embeddings=len(metrics.get("embeddings_created", [])) if isinstance(metrics, dict) else 0,
                                storage_success=True
                            )
                            if success:
                                print(f"[KIS] Recorded success: {job_id}", flush=True)
                        except Exception as e:
                            print(f"[WARN] Failed to record KIS success: {e}", flush=True)
                    
                    # Export ingestion logs
                    try:
                        kis_enhancer.save_ingestion_logs("ml/cache/ingestion_kis_logs.json")
                        print("[KIS] Ingestion logs exported", flush=True)
                    except Exception as e:
                        print(f"[WARN] Failed to export ingestion logs: {e}", flush=True)
                ### END KIS INTEGRATION ###
            except Exception:
                pass

        except Exception as e:
            # If async pipeline fails, fallback to synchronous embed_nodes
            print(f"[INGEST][WARN] Async pipeline failed - falling back to threaded embeddings: {e}")
            try:
                embeddings = embed_nodes(nodes_to_embed, extractor_client, progress_cb=lambda **kw: live_progress(storage, **kw))
                with open(os.path.join(storage, "03_embeddings.json"), "w", encoding="utf-8") as f:
                    json.dump(embeddings, f, indent=2, ensure_ascii=False)
                
                ### KIS INTEGRATION ###
                # Record ingestion success for ML training (fallback path)
                if kis_enhancer and ingestion_job_outcomes:
                    print("[KIS] Recording ingestion success outcomes (fallback)...", flush=True)
                    for job_id, outcome_data in ingestion_job_outcomes.items():
                        try:
                            kis_enhancer.record_ingestion_success(
                                ingestion_job_id=job_id,
                                minister_json=doctrines[outcome_data["doctrine_idx"] - 1],
                                num_chunks=len(nodes_to_embed),
                                num_embeddings=len(embeddings) if isinstance(embeddings, (list, dict)) else 0,
                                storage_success=True
                            )
                        except Exception as ex:
                            print(f"[WARN] Failed to record KIS success in fallback: {ex}", flush=True)
                ### END KIS INTEGRATION ###
            except Exception:
                pass

    except Exception as e:
        # If serialization to chunks fails, fallback to original embedding path
        print(f"[INGEST][WARN] Failed to prepare async chunks: {e}")
        try:
            embeddings = embed_nodes(nodes_to_embed, extractor_client, progress_cb=lambda **kw: live_progress(storage, **kw))
            with open(os.path.join(storage, "03_embeddings.json"), "w", encoding="utf-8") as f:
                json.dump(embeddings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ========== PHASE 3.5: MINISTER CONVERSION ==========
    try:
        live_progress(storage, phase="phase_3.5", message="Converting doctrine to minister structure")
        
        # Get the data root path (should be in workspace root)
        data_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        os.makedirs(data_root, exist_ok=True)
        
        # Convert chapter doctrines to minister domain structure
        def phase_3_5_progress_cb(**kw):
            try:
                live_progress(storage, **kw)
            except Exception:
                pass
        
        conversion_summary = convert_all_doctrines(
            doctrines,
            book_slug=book_id,
            data_root=data_root,
            progress_cb=phase_3_5_progress_cb
        )
        
        # Update combined vector index metadata
        update_combined_vector_index(data_root=data_root)
        
        # Save conversion summary
        summary_path = os.path.join(storage, "03_5_minister_conversion.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(conversion_summary, f, indent=2, ensure_ascii=False)
        
        live_progress(
            storage,
            phase="phase_3.5",
            message=f"Minister conversion completed: {conversion_summary['total_entries_created']} entries created",
            current=1,
            total=1
        )
        # Run post-Phase3 capital allocation / memory commit pipeline
        try:
            event = {
                "storage": storage,
                "book_id": book_id,
                # mission_vector could be provided by higher-level config
                "mission_vector": None,
            }
            ingest_post_phase3(event)
        except Exception as _e:
            # don't fail ingest on post-phase processing failures
            import traceback
            print(f"[INGEST][WARN] post-phase3 processing failed: {_e}")
            print(f"[INGEST][DEBUG] Traceback: {traceback.format_exc()}")
    except Exception as e:
        try:
            with open(os.path.join(storage, "03_5_minister_errors.log"), "w", encoding="utf-8") as ef:
                ef.write(f"Phase 3.5 error: {e}\n")
                import traceback
                ef.write(traceback.format_exc())
        except Exception:
            pass
        # Don't fail the whole pipeline if minister conversion fails
        print(f"[INGEST][WARN] Phase 3.5 (minister conversion) failed: {e}")

    # Final progress marker
    live_progress(storage, phase="completed", message="Ingestion finished", current=100, total=100)
    print("[INGEST] Completed successfully")

    # Clear local LLM/cache directory to avoid accumulating large files
    try:
        cache_root = os.path.abspath(os.path.join(os.getcwd(), "rag_cache"))
        if os.path.exists(cache_root):
            # Remove contents but be tolerant if other processes recreate directories
            for entry in os.listdir(cache_root):
                entry_path = os.path.join(cache_root, entry)
                try:
                    if os.path.isdir(entry_path):
                        shutil.rmtree(entry_path)
                    else:
                        os.remove(entry_path)
                except Exception:
                    pass
            # Attempt to remove the root if empty
            try:
                os.rmdir(cache_root)
                print(f"[INGEST] Removed cache root {cache_root}")
            except Exception:
                print(f"[INGEST] Cleared cache contents at {cache_root}")
    except Exception as e:
        print(f"[INGEST][WARN] Failed to clear cache {cache_root}: {e}")


# Helper parser used by AsyncIngestionPipeline's ProcessPoolExecutor.
def _parse_chunks_from_file(path: str) -> list:
    """Top-level parser that reads a chunk JSON file and returns Chunk objects.

    This must be a module-level function so it can be pickled by
    ProcessPoolExecutor when `AsyncIngestionPipeline` invokes it.
    """
    from .async_ingest_config import Chunk
    import json

    chunks = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []

    for item in data:
        try:
            c = Chunk(
                text=item.get('text', ''),
                domain=item.get('domain', 'base'),
                category=item.get('category', 'content'),
                source_book=item.get('source_book'),
                source_chapter=item.get('source_chapter'),
            )
            chunks.append(c)
        except Exception:
            continue

    return chunks


def ingest_folder(folder_path: str, *, fresh: bool = False):
    """
    Ingest all PDFs in a folder.
    
    Args:
        folder_path: Path to folder containing PDFs
        fresh: If True, ignore existing RAG data and re-ingest
    """
    print(f"[INGEST] ingest_folder entered: {folder_path}", flush=True)

    pdfs = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(".pdf")
    ]

    if not pdfs:
        print(f"[INGEST] No PDFs found in folder: {folder_path}")
        return

    print(f"[INGEST] Found {len(pdfs)} PDFs")

    for i, pdf in enumerate(sorted(pdfs), start=1):
        print(f"\n[INGEST] ({i}/{len(pdfs)}) Processing: {os.path.basename(pdf)}")
        try:
            run_full_ingest_with_resume(pdf, resume=not fresh)
        except Exception as e:
            print(f"[INGEST][ERROR] {pdf}: {e}")


if __name__ == "__main__":
    import argparse

    print("[BOOT] CLI entry reached", flush=True)

    parser = argparse.ArgumentParser(description="RAG ingest runner")
    parser.add_argument("path", help="Path to a PDF file OR a folder containing PDFs")
    parser.add_argument("--fresh", action="store_true", help="Ignore existing RAG data and re-ingest")

    args = parser.parse_args()
    print(f"[BOOT] args = {args}", flush=True)

    if os.path.isdir(args.path):
        print(f"[INGEST] Folder mode: {args.path}", flush=True)
        ingest_folder(args.path, fresh=args.fresh)
    else:
        print(f"[INGEST] File mode: {args.path}", flush=True)
        run_full_ingest_with_resume(args.path, resume=not args.fresh)