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
    Inline doctrine validation with resilient defaults.
    
    Fills in missing required keys with empty lists instead of failing.
    This allows extraction to continue even if the LLM omits a field.
    
    Args:
        doc: Doctrine object to validate
        context: Context string for error messages
        
    Returns:
        Validated doc with all required keys present
        
    Raises:
        RuntimeError: Only if doc is not a dict
    """
    if not isinstance(doc, dict):
        raise RuntimeError(f"[DOCTRINE][{context}] Output is not a dict: {type(doc)}")

    # Fill in missing keys with empty lists (resilient extraction)
    # This prevents extraction from failing if the LLM omits a field
    for key in REQUIRED_DOCTRINE_KEYS:
        if key not in doc:
            doc[key] = []
        elif not isinstance(doc[key], list):
            # If the key exists but is not a list, convert it or wrap it
            if isinstance(doc[key], str):
                doc[key] = [doc[key]] if doc[key].strip() else []
            else:
                doc[key] = []

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
                outs.append(f"{w.get('situation','')} {w.get('risk','')}".strip())
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
    # Perform a single extraction per chapter (no per-chunk LLM calls).
    # Truncate text for prompt size if extremely long to avoid overly large requests.
    max_chars = 8000
    chunk = text if len(text) <= max_chars else text[:max_chars]
    total_chunks = 1
    print(f"[DOCTRINE] Chapter {chapter_index} total_chunks={total_chunks}")

    if not text:
        raise RuntimeError(f"Phase 2 failed at chapter {chapter_index}: empty text")

    aggregated = {
        "domains": set(),
        "principles": [],
        "rules": [],
        "claims": [],
        "warnings": [],
    }

    # Load checkpoint state for resume support (chapter-level)
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
        # Reconstruct from completed chapter
        parsed_chunk = completed.get("0", {})
        aggregated["principles"].extend(parsed_chunk.get("principles", []))
        aggregated["rules"].extend(parsed_chunk.get("rules", []))
        aggregated["claims"].extend(parsed_chunk.get("claims", []))
        aggregated["warnings"].extend(parsed_chunk.get("warnings", []))
        for d in parsed_chunk.get("domains", []):
            # Normalize domain to string (handle both dict and string formats from LLM)
            if isinstance(d, dict):
                d = d.get("name") or str(d)
            aggregated["domains"].add(str(d))
    else:
        # Single per-chapter extraction
        if progress_cb:
            try:
                progress_cb(
                    chapter_index=chapter_index,
                    chunk_index=1,
                    total_chunks=1,
                )
            except Exception:
                pass

        parsed = _extract_chunk_doctrine(
            chunk,
            chapter_index,
            0,
            client,
            storage,
        )

        # Normalize domains to strings before storing (handle both dict and string formats)
        normalized_domains = []
        for d in parsed.get("domains", []):
            if isinstance(d, dict):
                d = d.get("name") or str(d)
            normalized_domains.append(str(d))

        # Checkpoint at chapter granularity
        chapter_state.setdefault("completed", {})["0"] = {
            "domains": normalized_domains,
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
        for d in normalized_domains:
            aggregated["domains"].add(str(d))

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

    # Validate structure; if invalid, return a safe fallback instead of raising so
    # downstream stages can continue and we retain an error marker per chapter.
    try:
        if not _is_doctrine_structurally_valid(result):
            raise RuntimeError(f"[DOCTRINE][chapter={chapter_index}] Invalid schema")
    except Exception as e:
        err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
        try:
            with open(err_path, "a", encoding="utf-8") as ef:
                ef.write(f"Chapter {chapter_index}: validation error: {e}\n")
                ef.write(json.dumps(result, ensure_ascii=False, indent=2))
                ef.write("\n---\n")
        except Exception:
            pass

        # Coerce a safe fallback doctrine object with required keys
        fallback = {
            "chapter_index": chapter_index,
            "chapter_title": chapter_title,
            "domains": sorted(aggregated["domains"]),
            "principles": aggregated.get("principles", []),
            "rules": aggregated.get("rules", []),
            "claims": aggregated.get("claims", []),
            "warnings": aggregated.get("warnings", []),
            "_status": "extraction_failed",
            "_error": str(e),
        }

        return fallback

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
    # Do NOT print chunk text to stdout (sensitive / large). The prompt includes the
    # necessary text but we avoid echoing it to logs.

    # Build prompt without f-string braces to avoid accidental format parsing
    json_skeleton = (
        '{\n'
        '    "domains": [],\n'
        '    "principles": [],\n'
        '    "rules": [],\n'
        '    "claims": [],\n'
        '    "warnings": []\n'
        '}'
    )

    user_prompt = (
        "RETURN JSON WITH THIS EXACT STRUCTURE:\n\n"
        + json_skeleton
        + "\n\nCHAPTER INDEX: "
        + str(chapter_index)
        + "\n\nTEXT (for analysis only — DO NOT QUOTE):\n"
        + "--------------------------------------\n"
        + chunk[:8000]
        + "\n--------------------------------------\n\n"
        + "INSTRUCTIONS:\n"
        + "1. Select 1–3 applicable DOMAINS from the provided list.\n"
        + "2. Extract actionable operational content: ANY principles, rules, decision criteria, warnings, or claims.\n"
        + "3. Generalize: convert specific examples into abstract, normalized language.\n"
        + "4. Do not quote; paraphrase and abstract.\n\n"
        + "EXTRACTION REQUIREMENTS:\n"
        + "- IF the text contains operational guidance (advice, lessons, decision rules, warnings), EXTRACT IT.\n"
        + "- If any field seems empty, infer from context (e.g., infer rules from principles).\n"
        + "- PREFERENCE: Over-extraction is better than under-extraction.\n"
        + "- MINIMUM TARGET: If guidance exists, aim for at least 1–2 items per field (principles, rules, claims, warnings).\n"
        + "- DOMAINS MUST NOT BE EMPTY.\n\n"
        + "EXAMPLES OF OPERATIONAL CONTENT:\n"
        + "- [Financial book] 'Save before you spend' → principle; 'Never spend principal' → rule; 'Compound interest builds wealth' → claim.\n"
        + "- [Management text] 'Delegate effectively' → principle; 'Set clear expectations' → rule; 'Unclear delegation causes failure' → warning.\n"
        + "- [Narrative with lessons] ANY learning, advice, or cautionary element = extract.\n\n"
        + "If the text has NO operational content, return minimal but valid JSON with at least domains populated.\n"
    )

    user_prompt_retry = user_prompt + (
        "\nRETRY MODE:\n"
        "- Paraphrase aggressively\n"
        "- Reduce sentence length\n"
        "- Prefer generalized verbs\n"
        "- If possible, satisfy the minimum extraction counts listed above\n"
    )

    parsed = None
    last_err = None
    
    for attempt in (1, 2):
        try:
            prompt_to_use = user_prompt if attempt == 1 else user_prompt_retry
            parsed = call_json_llm_strict(
                prompt=prompt_to_use,
                system=SYSTEM_PROMPT_DOCTRINE,
                client=client,
                timeout=30,  # Reduced from 60s for faster local execution
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