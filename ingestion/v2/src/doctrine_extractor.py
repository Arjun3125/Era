"""Doctrine extraction and validation logic."""
from __future__ import annotations

import json
import os
import re
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
    """Inline doctrine validation. Hard fail if structure invalid."""
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
    """Detect verbatim quoted spans from source text."""
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
    **_kwargs,
) -> Dict[str, Any]:
    """Extract abstracted doctrine from a chapter using LLM."""
    chapter_index = chapter.get("chapter_index") or _kwargs.get("chapter_index", 1)
    chapter_title = chapter.get("chapter_title") or _kwargs.get("chapter_title", f"Chapter {chapter_index}")
    
    text = chapter.get("raw_text") or chapter.get("text") or ""
    chapter_id = chapter.get("chapter_id") or sha(text)
    
    chunks = chunk_text(text, chunk_size=8000)
    total_chunks = len(chunks)
    print(f"[DOCTRINE] Chapter {chapter_index} total_chunks={total_chunks}")

    if not chunks:
        # Return valid empty if no text
        return {
            "chapter_index": chapter_index,
            "chapter_title": chapter_title,
            "domains": ["strategy"],
            "principles": [],
            "rules": [],
            "claims": [],
            "warnings": [],
            "_status": "valid_empty"
        }

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
        "domains": sorted(aggregated["domains"]) or ["strategy"],
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
    """Extract doctrine from a single text chunk with retry logic."""
    user_prompt = f"""
RETURN JSON WITH THIS EXACT STRUCTURE:

{{
    "domains": [],
    "principles": [],
    "rules": [],
    "claims": [],
    "warnings": []
}}

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
