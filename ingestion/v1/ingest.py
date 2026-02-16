#!/usr/bin/env python3
# ingest_v2.py — pagewise, phase-correct ingestion runner

import os
import sys
import time
import argparse
import json
import hashlib
import re
from typing import List, Dict, Any, Optional

from pypdf import PdfReader
from pdfminer.high_level import extract_text as pdfminer_extract
import subprocess
import tempfile
import shutil
import unicodedata
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

# Parallelism tuning
MAX_WORKERS = 4  # tune between 2-6 depending on system

# Token / chunk sizing (approximate)
MAX_TOKENS = 2000
MAX_CHARS = int(MAX_TOKENS * 3.5)

# LLM result cache
CACHE_DIR = os.path.join("rag_cache", "llm")
os.makedirs(CACHE_DIR, exist_ok=True)

# make local `llm.py` importable from this folder
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from llm import (
    OllamaClient,
    call_json_llm_strict,
    embed_nodes,
    build_minister_memories,
    DEFAULT_EXTRACT_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
)

# Ensure prints flush reliably on Windows consoles
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

print("[BOOT] ingest_v2.py loaded", flush=True)


# ============================================================
# Utilities
# ============================================================

# ============================================================
# Phase 2 	6 Doctrine Validation
# ============================================================
# Inline doctrine validation (replaces rag.validate_doctrine)
REQUIRED_DOCTRINE_KEYS = {
    "domains",
    "principles",
    "rules",
    "claims",
    "warnings",
}


def validate_doctrine_inline(doc: dict, *, context: str) -> dict:
    """
    Inline doctrine validation. HARD FAIL if structure is wrong.
    """
    if not isinstance(doc, dict):
        raise RuntimeError(f"[DOCTRINE][{context}] Output is not a dict: {type(doc)}")

    for key in REQUIRED_DOCTRINE_KEYS:
        if key not in doc:
            raise RuntimeError(f"[DOCTRINE][{context}] Missing key: {key}")
        if not isinstance(doc[key], list):
            raise RuntimeError(f"[DOCTRINE][{context}] Key '{key}' is not a list")

    return doc


def reject_verbatim_quotes_inline(doc: dict, raw_text: str, *, context: str, min_words: int = 12) -> None:
    """
    Detect verbatim quoted spans: if any contiguous sequence of >= `min_words`
    words from the raw_text appears verbatim in a doctrine item, raise.
    """
    if not raw_text:
        return

    raw_norm = re.sub(r"\s+", " ", raw_text).lower()
    # build set of n-word substrings from the raw text for quick membership
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
                    raise RuntimeError(f"[DOCTRINE][{context}] Verbatim phrase detected: '{phrase[:80]}...'")

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, *, max_chars: int = 8000) -> list[str]:
    # Token-aware chunking: use MAX_CHARS by default to avoid token overflows
    max_c = max_chars or MAX_CHARS
    out: list[str] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + max_c, n)
        cut = text.rfind("\n\n", start, end)
        if cut == -1 or cut <= start:
            cut = end
        out.append(text[start:cut])
        start = cut

    return [c for c in out if c.strip()]


def dedupe_list(items):
    """
    Deterministically deduplicate a list while preserving order.
    Safe for strings or dicts.
    """
    seen = set()
    out = []

    for item in items:
        key = (
            json.dumps(item, sort_keys=True, ensure_ascii=False)
            if isinstance(item, dict)
            else str(item)
        )
        if key not in seen:
            seen.add(key)
            out.append(item)

    return out


def looks_glyph_encoded(text: str, *, threshold: float = 0.08) -> bool:
    """
    Stricter glyph heuristic: use non-ASCII density and unicode category signals.
    Returns True when multiple signals indicate font-encoding artifacts.
    """
    if not text:
        return False

    total = len(text)
    if total == 0:
        return False

    non_ascii = sum(1 for c in text if ord(c) > 127)
    non_ascii_ratio = non_ascii / max(total, 1)

    weird = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("C") or cat.startswith("S"):
            weird += 1
    weird_ratio = weird / max(total, 1)

    # require both a high non-ascii ratio and substantial weird char ratio
    return (non_ascii_ratio > 0.15 and weird_ratio > 0.05) or (weird_ratio > 0.12)


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


def split_chapters_with_ollama_streaming(
    pages: list[str],
    *,
    client,
    book_title: str | None = None,
    storage: str | None = None,
) -> list[dict]:
    """
    Phase 1 (NEW): Ollama-driven streaming chapter detection.
    Deterministic wrapper, LLM used only for boundary decisions.
    """

    chapters = []
    buffer = ""
    chapter_index = 0

    def flush_buffer():
        nonlocal buffer, chapter_index
        if not buffer.strip():
            return
        chapter_index += 1
        chapters.append({
            "chapter_index": chapter_index,
            "chapter_id": sha(buffer),
            "chapter_title": None,
            "raw_text": buffer.strip(),
        })
        buffer = ""


    for page_no, page in enumerate(pages, start=1):
        # Emit lightweight progress so the UI/console updates during long LLM calls
        try:
            if storage:
                live_progress(storage, phase="phase_1", message=f"Chapter split: processing page {page_no}/{len(pages)}", current=page_no, total=len(pages))
        except Exception:
            pass
        page_text = page.strip()
        if not page_text:
            buffer += "\n\f\n"
            continue

        user_prompt = f"""
CURRENT BUFFER (tail only):
--------------------------
{buffer[-4000:]}
--------------------------

NEW PAGE TEXT:
--------------------------
{page_text[:4000]}
--------------------------

QUESTION:
Does this page START a new chapter, CONTINUE the current chapter,
or END the current chapter?

Return JSON exactly:
{{
  "decision": "start_new_chapter | continue_chapter | end_chapter",
  "confidence": 0.0
}}
"""

        try:
            cache_key = sha(PHASE1_SYSTEM_PROMPT + user_prompt)
            cache_path = os.path.join(CACHE_DIR, cache_key + ".json")
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as cf:
                        decision = json.load(cf)
                except Exception:
                    decision = call_json_llm_strict(prompt=user_prompt, system=PHASE1_SYSTEM_PROMPT, client=client)
                    try:
                        with open(cache_path, "w", encoding="utf-8") as cf:
                            json.dump(decision, cf, ensure_ascii=False)
                    except Exception:
                        pass
            else:
                decision = call_json_llm_strict(prompt=user_prompt, system=PHASE1_SYSTEM_PROMPT, client=client)
                try:
                    with open(cache_path, "w", encoding="utf-8") as cf:
                        json.dump(decision, cf, ensure_ascii=False)
                except Exception:
                    pass
        except Exception:
            decision = {"decision": "continue_chapter"}

        action = decision.get("decision", "continue_chapter")

        if action == "start_new_chapter":
            flush_buffer()
            buffer = page_text
        elif action == "end_chapter":
            buffer += "\n\f\n" + page_text
            flush_buffer()
        else:
            buffer += "\n\f\n" + page_text

    # flush final chapter and return
    flush_buffer()

    # safety: ensure at least one chapter
    if not chapters:
        chapters = [{
            "chapter_index": 1,
            "chapter_id": sha("\n".join(pages)),
            "chapter_title": book_title,
            "raw_text": "\n\f\n".join(pages),
        }]

    return chapters


def fallback_split_by_headings(text: str) -> list[dict]:
    """Fallback splitter that uses common book heading patterns to break
    a canonical text into chapters when the LLM-driven splitter fails.

    It looks for headings like "THE FIRST BOOK", "BOOK I", "CHAPTER 1",
    or similar uppercase markers and splits the text at those positions.
    """
    import re

    if not text or not text.strip():
        return []

    # candidate heading regexes (multiline, match at line start)
    patterns = [
        r'(?m)^(THE\s+[A-Z ]+BOOK)\b',
        r'(?m)^(BOOK\s+[IVXLCDM]+)\b',
        r'(?m)^(CHAPTER\s+\d+)\b',
        r'(?m)^(THE\s+[A-Z]+)\b',
    ]

    # find all heading matches
    matches = []
    for p in patterns:
        for m in re.finditer(p, text):
            matches.append((m.start(), m.group(0)))

    # dedupe and sort by position
    matches = sorted({pos: hdr for pos, hdr in matches}.items())

    # If we didn't find useful headings, return single-chapter fallback
    if len(matches) <= 1:
        return [
            {
                "chapter_index": 1,
                "chapter_id": sha(text),
                "chapter_title": None,
                "raw_text": text,
            }
        ]

    chapters = []
    positions = [pos for pos, _ in matches]
    positions.append(len(text))

    for i in range(len(positions) - 1):
        start = positions[i]
        end = positions[i + 1]
        chunk = text[start:end].strip()
        if not chunk:
            continue
        chapters.append(
            {
                "chapter_index": len(chapters) + 1,
                "chapter_id": sha(chunk),
                "chapter_title": None,
                "raw_text": chunk,
            }
        )

    # safety: ensure at least one chapter
    if not chapters:
        chapters = [
            {
                "chapter_index": 1,
                "chapter_id": sha(text),
                "chapter_title": None,
                "raw_text": text,
            }
        ]

    return chapters

def text_quality_score(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(1 for c in text if c.isprintable())
    return printable / max(len(text), 1)


def is_glyph_stream(text: str) -> bool:
    return bool(re.search(r'/G[0-9A-Fa-f]{2}', text))


# (see custom `looks_glyph_encoded` implementation above)


def extract_with_pypdf(path: str) -> str:
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return "\f".join(pages)


def extract_pdf_pages(pdf_path: str, storage: Optional[str] = None) -> list[str]:
    """
    Deterministic, page-wise extraction.
    This is the ONLY function Phase 0 should call.
    """
    reader = PdfReader(pdf_path)
    pages = []
    total = len(reader.pages)
    for i, p in enumerate(reader.pages, start=1):
        try:
            text = p.extract_text() or ""
            # emit per-page live progress when storage available
            if storage:
                try:
                    live_progress(
                        storage,
                        phase="phase_0",
                        message="Extracting PDF pages",
                        current=i,
                        total=total,
                    )
                except Exception:
                    pass
            pages.append(text)
        except Exception:
            pages.append("")
    return pages


def extract_with_pdfminer(path: str) -> str:
    try:
        return pdfminer_extract(path) or ""
    except Exception:
        return ""


def extract_with_ocr(path: str) -> str:
    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract not installed; OCR required but unavailable")

    with tempfile.TemporaryDirectory() as tmp:
        img_prefix = os.path.join(tmp, "page")

        subprocess.run(
            ["pdftoppm", path, img_prefix, "-png"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        texts = []
        for img in sorted(os.listdir(tmp)):
            if img.endswith(".png"):
                img_path = os.path.join(tmp, img)
                txt = subprocess.check_output(
                    ["tesseract", img_path, "stdout"],
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8", errors="ignore")
                texts.append(txt)

        return "\f".join(texts)


def extract_text_universal(pdf_path: str) -> str:
    # Phase 0 — pypdf
    text = extract_with_pypdf(pdf_path)
    score = text_quality_score(text)

    if score > 0.85 and not is_glyph_stream(text):
        return text

    # Phase 0.25 — pdfminer
    text2 = extract_with_pdfminer(pdf_path)
    score2 = text_quality_score(text2)

    if score2 > score and score2 > 0.85 and not is_glyph_stream(text2):
        return text2

    # Phase 0.75 — OCR (last resort)
    return extract_with_ocr(pdf_path)


def repair_glyph_text(text: str, *, client: OllamaClient, storage: str) -> str:
    """
    One-shot glyph repair using LLM.
    Cached by content hash.
    """
    key = sha("glyph_repair" + text)
    cache_path = os.path.join(storage, f"glyph_repair_{key}.txt")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass

    prompt = f"""
The following text contains font-encoding or glyph artifacts.
Repair it into clean, readable English.
Do not summarize or omit content.

TEXT:
{text[:12000]}
"""
    try:
        repaired = client.generate(prompt).strip()
    except Exception:
        repaired = text

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(repaired)
    except Exception:
        pass

    return repaired


# PHASE 1 — Structural segmentation is handled by `split_chapters_with_ollama_streaming` above.
# Legacy helpers and duplicate prompts removed.


# Legacy heuristic splitter removed per request — Phase‑1 is now LLM-driven.


# ============================================================
# PHASE 2 — Doctrine extraction
# ============================================================

# Hard-coded allowed domains for doctrine extraction. Model must choose 1-3.
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

# Lightweight keyword mapping to infer domains when the model omits them.
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


def infer_domains_from_text(text: str, max_domains: int = 3):
    lc = (text or "").lower()
    scores = {}
    for d, kws in DOMAIN_KEYWORDS.items():
        s = 0
        for kw in kws:
            s += lc.count(kw)
        if s > 0:
            scores[d] = s
    if not scores:
        return ["strategy"]
    # sort by score desc and return top N
    ordered = sorted(scores.items(), key=lambda x: -x[1])
    return [d for d, _ in ordered[:max_domains]]


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


def extract_doctrine(
    chapter: Dict[str, Any],
    *,
    client: OllamaClient,
    progress_cb=None,
    storage: Optional[str] = None,
) -> Dict[str, Any]:
    chapter_index = chapter["chapter_index"]
    chapter_title = chapter.get("chapter_title")
    chapter_id = chapter.get("chapter_id") or sha(chapter.get("raw_text", ""))

    base_schema = {
        "chapter_index": chapter_index,
        "chapter_title": chapter_title,
        "domains": [],
        "principles": [],
        "rules": [],
        "claims": [],
        "warnings": [],
    }

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

    # checkpoint file for doctrine chunks
    doctrine_path = os.path.join(storage, "02_doctrine_chunks.json") if storage else None
    if doctrine_path and os.path.exists(doctrine_path):
        try:
            with open(doctrine_path, "r", encoding="utf-8") as f:
                doctrine_state = json.load(f)
        except Exception:
            doctrine_state = {}
    else:
        doctrine_state = {}


    # use a content-hash based chapter key for resumable checkpoints
    chapter_key = f"chapter_{chapter_id}"
    chapter_state = doctrine_state.get(chapter_key, {"total_chunks": total_chunks, "completed": {}})

    # If all chunks already completed, reconstruct and return deterministically
    completed = chapter_state.get("completed", {})
    if len(completed) == total_chunks and total_chunks > 0:
        print(f"[PHASE 2] Chapter {chapter_index} already completed — skipping")
        # rebuild aggregated from completed parsed chunks
        for i in range(total_chunks):
            parsed_chunk = completed.get(str(i), {})
            aggregated["principles"].extend(parsed_chunk.get("principles", []))
            aggregated["rules"].extend(parsed_chunk.get("rules", []))
            aggregated["claims"].extend(parsed_chunk.get("claims", []))
            aggregated["warnings"].extend(parsed_chunk.get("warnings", []))
            # rehydrate domains if present
            for d in parsed_chunk.get("domains", []):
                aggregated["domains"].add(d)

        # proceed to result construction below

    for i, chunk in enumerate(chunks):
        # report progress (1-based chunk index for UI)
        if progress_cb:
            try:
                progress_cb(chapter_index=chapter_index, chunk_index=i + 1, total_chunks=total_chunks)
            except Exception:
                pass

        # simple instrumentation for visibility
        print(
            f"[DOCTRINE] Chapter {chapter_index} Chunk {i+1}/{total_chunks} ({len(chunk)} chars)"
        )

        idx = str(i)
        if idx in chapter_state.get("completed", {}):
            parsed = chapter_state["completed"][idx]
        else:
            # User prompt follows the strict template to force abstraction, not copying
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

            # Try extraction with one retry on verbatim-detection
            parsed = None
            last_err = None
            # build a retry prompt variant for forced paraphrase on attempt 2
            user_prompt_retry = user_prompt + """
RETRY MODE:
- Paraphrase aggressively
- Reduce sentence length
- Prefer generalized verbs
"""

            for attempt in (1, 2):
                try:
                    prompt_to_use = user_prompt if attempt == 1 else user_prompt_retry
                    parsed = call_json_llm_strict(
                        prompt=prompt_to_use,
                        system=SYSTEM_PROMPT_DOCTRINE,
                        client=client,
                    )

                    # basic type check
                    if not isinstance(parsed, dict):
                        raise ValueError("Parsed chunk is not a JSON object")

                    # Ensure domains BEFORE validation (guarantee, not retry)
                    if not parsed.get("domains"):
                        parsed["domains"] = infer_domains_from_text(chunk)
                        # log fallback
                        err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
                        try:
                            with open(err_path, "a", encoding="utf-8") as ef:
                                ef.write(f"Chapter {chapter_index}, chunk {i+1}: domains missing from model; inferred {parsed['domains']}\n")
                        except Exception:
                            pass

                    # structural validation and anti-quote check (inline)
                    validate_doctrine_inline(parsed, context=f"chapter={chapter_index},chunk={i+1}")
                    try:
                        reject_verbatim_quotes_inline(parsed, chunk, context=f"chapter={chapter_index},chunk={i+1}")
                    except RuntimeError as rv_err:
                        # Downgrade verbatim detection to a warning on the parsed chunk
                        parsed["_verbatim_warning"] = str(rv_err)

                    # success
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    # log error for this attempt
                    err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
                    try:
                        with open(err_path, "a", encoding="utf-8") as ef:
                            ef.write(f"Chapter {chapter_index} chunk {i+1} attempt {attempt} error: {e}\n")
                    except Exception:
                        pass
                    parsed = None

            if parsed is None:
                # After retrying, we couldn't get valid doctrine for this chunk — raise an error
                raise RuntimeError(f"Doctrine extraction failed: chapter={chapter_index} chunk={i+1}: {last_err}") from last_err

            # checkpoint this parsed chunk (store domains + atoms)
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

        for k in ("principles", "rules", "claims", "warnings"):
            aggregated[k].extend(parsed.get(k, []))
        # aggregate domains
        for d in parsed.get("domains", []):
            aggregated["domains"].add(d)

    # Apply semantic dedupe to aggregated lists to avoid noisy duplicates
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

# Structural validation helpers
    def is_doctrine_structurally_valid(d):
        return (
            isinstance(d, dict)
            and "domains" in d
            and "principles" in d
            and "rules" in d
            and "claims" in d
            and "warnings" in d
        )


    def has_actionable_doctrine(d):
        return any([
            len(d.get("principles", [])) > 0,
            len(d.get("rules", [])) > 0,
            len(d.get("claims", [])) > 0,
            len(d.get("warnings", [])) > 0,
        ])

    # Validate schema first — if schema is invalid, that's an error
    if not is_doctrine_structurally_valid(result):
        err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
        try:
            with open(err_path, "a", encoding="utf-8") as ef:
                ef.write(f"[ERROR] [DOCTRINE] Invalid schema for chapter {chapter_index}\n")
        except Exception:
            pass
        raise RuntimeError(f"[DOCTRINE] Invalid schema for chapter {chapter_index}")

    # If the schema is valid but contains no actionable doctrine, mark as valid_empty
    # Do not raise, do not write an error log; print an INFO-style message instead
    if not has_actionable_doctrine(result):
        print(f"[DOCTRINE] Chapter {chapter_index}: no actionable doctrine (valid_empty)")
        result["_status"] = "valid_empty"

        # On success, print summary counts
        print(
            f"[DOCTRINE] Extracted {len(result.get('principles', []))} principles, {len(result.get('rules', []))} rules, {len(result.get('claims', []))} claims, {len(result.get('warnings', []))} warnings for chapter {chapter_index}"
        )

        return result

    # For non-empty (actionable) doctrine, return the constructed result
    return result


# ============================================================
# PHASE 2.5 — Atomic doctrine nodes
# ============================================================

def doctrine_to_nodes(doctrine: Dict[str, Any], prefix: str) -> List[Dict[str, Any]]:
    # New behavior: accept strict doctrine schema with lists of objects
    nodes: List[Dict[str, Any]] = []
    idx = doctrine["chapter_index"]
    short_book = prefix.replace("\n", "").upper()

    counters = {"principle": 0, "rule": 0, "warning": 0, "claim": 0}

    # principles -> create nodes using provided id when possible
    for p in doctrine.get("principles", []):
        pid = p.get("id") or None
        counters["principle"] += 1
        seq = counters["principle"]
        id_part = pid if pid else f"P{seq:03d}"
        node_id = f"{short_book}-C{idx:02d}-P-{id_part}"
        nodes.append({
            "node_id": node_id,
            "type": "principle",
            "text": p.get("statement"),
            "metadata": {"chapter": idx, "abstracted_from": p.get("abstracted_from")},
        })

    # rules -> condition/action
    for r in doctrine.get("rules", []):
        counters["rule"] += 1
        seq = counters["rule"]
        node_id = f"{short_book}-C{idx:02d}-R-{seq:03d}"
        # represent rule as IF -> THEN text for embedding
        text = f"IF {r.get('condition')} THEN {r.get('action')}"
        nodes.append({
            "node_id": node_id,
            "type": "rule",
            "text": text,
            "metadata": {"chapter": idx},
        })

    # warnings
    for w in doctrine.get("warnings", []):
        counters["warning"] += 1
        seq = counters["warning"]
        node_id = f"{short_book}-C{idx:02d}-W-{seq:03d}"
        text = f"SITUATION: {w.get('situation')}. RISK: {w.get('risk')}"
        nodes.append({
            "node_id": node_id,
            "type": "warning",
            "text": text,
            "metadata": {"chapter": idx},
        })

    # claims
    for c in doctrine.get("claims", []):
        counters.setdefault("claim", 0)
        counters["claim"] += 1
        seq = counters["claim"]
        node_id = f"{short_book}-C{idx:02d}-L-{seq:03d}"
        text = f"CLAIM: {c.get('claim')}"
        nodes.append({
            "node_id": node_id,
            "type": "claim",
            "text": text,
            "metadata": {"chapter": idx, "confidence": c.get("confidence")},
        })

    return nodes


# ============================================================
# Progress tracking
# ============================================================

def update_progress(
    out_dir: str,
    *,
    phase: str,
    phase_name: str,
    status: str,
    percent: int = 0,
    counts: dict | None = None,
):
    # Centralize all progress writes through `live_progress` so we have
    # a single source-of-truth and consistent on-disk format (with
    # backward-compatible legacy keys).
    try:
        # map percent (0-100) to current/total for live_progress if possible
        if percent is not None and isinstance(percent, int):
            # represent percent as current out of 100
            current = percent
            total = 100
        else:
            current = None
            total = None

        live_progress(
            out_dir,
            phase=phase,
            message=f"{phase_name} - {status}",
            current=current,
            total=total,
        )
    except Exception:
        # best-effort fallback to legacy file format
        try:
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, "progress.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "current_phase": phase,
                    "current_phase_name": phase_name,
                    "status": status,
                    "percent": percent,
                    "counts": counts or {},
                }, f, indent=2)
        except Exception:
            pass


def live_progress(
    storage: str,
    phase: str,
    message: str,
    *,
    current: Optional[int] = None,
    total: Optional[int] = None,
):
    payload = {
        "phase": phase,
        "message": message,
        "current": current,
        "total": total,
        "timestamp": time.time(),
    }

    # Console (human)
    if current is not None and total is not None:
        try:
            print(f"[{phase.upper()}] {message} ({current}/{total})", flush=True)
        except Exception:
            pass
    else:
        try:
            print(f"[{phase.upper()}] {message}", flush=True)
        except Exception:
            pass

    # progress.json (machine) — include legacy keys for backward compatibility
    try:
        path = os.path.join(storage, "progress.json")
        os.makedirs(storage, exist_ok=True)

        # legacy compatibility layer
        legacy = {
            "current_phase": phase,
            "current_phase_name": message,
            "status": ("completed" if (current is not None and total is not None and current >= total) or phase == "completed" else "running"),
            "percent": int((current / total) * 100) if (current is not None and total) else (100 if phase == "completed" else 0),
            "counts": {"current": current, "total": total},
        }

        merged = {**payload, **legacy}

        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
    except Exception:
        pass


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def run_full_ingest_with_resume(pdf_path: str, resume: bool = True):
    book_id = os.path.splitext(os.path.basename(pdf_path))[0]
    storage = os.path.join("rag_storage", book_id)
    os.makedirs(storage, exist_ok=True)

    # Fast skip: if resuming and the book already completed, skip full ingest.
    try:
        progress_path = os.path.join(storage, "progress.json")
        emb_path = os.path.join(storage, "03_embeddings.json")
        if resume:
            if os.path.exists(progress_path):
                try:
                    with open(progress_path, "r", encoding="utf-8") as pf:
                        prog = json.load(pf)
                    # Accept either legacy `current_phase` or new `phase` key
                    finished = False
                    if prog.get("current_phase") == "completed":
                        finished = True
                    if prog.get("phase") == "completed":
                        finished = True
                    # also allow status/percent interpretation
                    if prog.get("status") == "completed":
                        finished = True
                    if finished:
                        print(f"[INGEST] Skipping {book_id}: already completed (progress.json)", flush=True)
                        return
                except Exception:
                    pass
            if os.path.exists(emb_path):
                print(f"[INGEST] Skipping {book_id}: embeddings present", flush=True)
                return
    except Exception:
        pass

    # create two explicit clients: extractor (qwen3) and doctrine/deepseek
    extractor_client = OllamaClient(model=DEFAULT_EXTRACT_MODEL)
    doctrine_client = OllamaClient(model=DEFAULT_DEEPSEEK_MODEL)

    # Phase 0: raw extraction -> canonical text persistence
    live_progress(storage, phase="phase_0", message="Starting PDF extraction")
    pages = extract_pdf_pages(pdf_path, storage=storage)
    raw = "\f".join(pages)

    # --------
    # PHASE 0.5 — glyph repair (guarded, chunked)
    # --------
    repaired_path = os.path.join(storage, "00_raw_repaired.txt")
    # If resuming and a repaired artifact exists, reuse it to save time.
    if resume and os.path.exists(repaired_path):
        try:
            with open(repaired_path, "r", encoding="utf-8") as f:
                raw = f.read()
            live_progress(storage, phase="phase_0.5", message="Using cached repaired raw text (resume)")
        except Exception:
            # fall through to detection/repair below
            pass
    else:
        # Only run repair when the heuristic triggers
        if looks_glyph_encoded(raw):
            # Chunk raw text and repair chunk-by-chunk to provide live feedback
            chunks = chunk_text(raw, max_chars=MAX_CHARS)
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
            live_progress(storage, phase="phase_0.5", message="Glyph repair completed", current=total_chunks, total=total_chunks)

    # Persist raw and canonical text. From this point forward canonical_text
    # is the single source of truth for downstream phases.
    canonical_path = os.path.join(storage, "00_canonical_text.txt")
    with open(os.path.join(storage, "00_raw.txt"), "w", encoding="utf-8") as f:
        f.write(raw)
    with open(canonical_path, "w", encoding="utf-8") as f:
        f.write(raw)
    live_progress(storage, phase="phase_0", message="PDF extraction completed")

    # PHASE 1: chapter split (OLLAMA STREAMING)
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
        # If LLM splitter returned a single chapter for a long canonical text,
        # try a deterministic fallback using heading patterns (e.g., THE FIRST BOOK,
        # BOOK I, CHAPTER 1). This handles well-structured books when the model
        # doesn't produce strict JSON for boundary decisions.
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

    live_progress(storage, phase="phase_1", message="Chapter split (LLM) completed", current=len(chapters), total=len(chapters))

    # Phase 2
    live_progress(storage, phase="phase_2", message="Doctrine extraction started")
    doctrines = []
    errors: list[str] = []
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
    for i, ch in enumerate(chapters, start=1):
        live_progress(
            storage,
            phase="phase_2",
            message=f"Processing chapter {i}/{total}",
            current=i - 1,
            total=total,
        )
        # Debug: show chapter index and raw_text length to diagnose empty inputs
        raw_len = len(ch.get("raw_text", "") if isinstance(ch, dict) else "")
        print(f"[PHASE 2] Chapter {i} index={ch.get('chapter_index')} id={ch.get('chapter_id')} raw_length={raw_len}")
        chapter_success = False
        try:
            doc = extract_doctrine(
                ch,
                client=doctrine_client,
                progress_cb=phase2_progress,
                storage=storage,
            )
            doctrines.append(doc)
            chapter_success = True
        except (ModuleNotFoundError, ImportError) as e:
            # Critical import error — fail fast
            raise RuntimeError(f"Critical import failure during doctrine extraction: {e}") from e
        except Exception as e:
            # Non-critical extraction error for this chapter — attempt to recover any completed chunk parses
            err_path = os.path.join(storage or ".", "02_doctrine_errors.log")
            try:
                with open(err_path, "a", encoding="utf-8") as ef:
                    ef.write(f"Chapter {i} extraction error: {e}\n")
            except Exception:
                pass

            # Try to reconstruct from checkpointed chunk parses if any exist
            doctrine_path = os.path.join(storage or ".", "02_doctrine_chunks.json")
            reconstructed = None
            try:
                if os.path.exists(doctrine_path):
                    with open(doctrine_path, "r", encoding="utf-8") as f:
                        dstate = json.load(f)
                    chapter_id = ch.get("chapter_id") or sha(ch.get("raw_text", ""))
                    chapter_key = f"chapter_{chapter_id}"
                    chap_state = dstate.get(chapter_key, {})
                    completed = chap_state.get("completed", {})
                    if completed:
                        # aggregate available parsed chunks
                        agg = {"domains": set(), "principles": [], "rules": [], "claims": [], "warnings": []}
                        for idx in sorted(completed.keys(), key=lambda x: int(x)):
                            parsed_chunk = completed.get(idx, {})
                            for k in ("principles", "rules", "claims", "warnings"):
                                agg[k].extend(parsed_chunk.get(k, []))
                            for dname in parsed_chunk.get("domains", []):
                                agg["domains"].add(dname)
                        reconstructed = {
                            "chapter_index": ch.get("chapter_index"),
                            "chapter_title": ch.get("chapter_title"),
                            "domains": sorted(agg["domains"]),
                            "principles": agg["principles"],
                            "rules": agg["rules"],
                            "claims": agg["claims"],
                            "warnings": agg["warnings"],
                        }
            except Exception:
                reconstructed = None

            if reconstructed:
                # Partial success: some chunks produced doctrine
                doctrines.append(reconstructed)
                chapter_success = True
                # log a warning about partial failures
                try:
                    with open(err_path, "a", encoding="utf-8") as ef:
                        ef.write(f"Chapter {i} partial success: reconstructed from {len(reconstructed.get('principles', []))} principles etc.\n")
                except Exception:
                    pass
            else:
                # No parsed chunks — record chapter-level failure and add empty doctrine placeholder
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
                try:
                    with open(err_path, "a", encoding="utf-8") as ef:
                        ef.write(f"Chapter {i} produced no doctrine and was marked failed.\n")
                except Exception:
                    pass

    # Sanity check before writing: ensure each doctrine is a dict and log keys
    for idx, d in enumerate(doctrines, start=1):
        if not isinstance(d, dict):
            raise RuntimeError(f"Doctrine object for chapter {idx} is not a dict: {type(d)}")
        try:
            print(f"[DEBUG] Doctrine keys for chapter {idx}: {list(d.keys())}")
        except Exception:
            pass

    # ------------------------------------------------------------
    # Augment each doctrine with a system-owned _meta block
    # ------------------------------------------------------------
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

    def classify_chapter(doctrine_obj, raw_text):
        # Deterministic heuristic-first classifier
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

        narrative_markers = [
            "story", "example", "illustration",
            "history", "background", "context",
            "in this chapter", "we will see"
        ]

        if any(m in text for m in narrative_markers):
            return "narrative"

        return "commentary"

    def doctrine_density(d, raw_text):
        count = (
            len(d.get("principles", []) or []) +
            len(d.get("rules", []) or []) +
            len(d.get("claims", []) or []) +
            len(d.get("warnings", []) or [])
        )
        return round(count / max(len((raw_text or "").split()), 1), 4)

    # Load chunk-level checkpoint state if present to report extracted_chunks
    doctrine_chunks_path = os.path.join(storage, "02_doctrine_chunks.json")
    try:
        if os.path.exists(doctrine_chunks_path):
            with open(doctrine_chunks_path, "r", encoding="utf-8") as f:
                chunks_state = json.load(f)
        else:
            chunks_state = {}
    except Exception:
        chunks_state = {}

    # Enrich doctrines in-place; chapters list corresponds by index
    for idx, d in enumerate(doctrines, start=1):
        # find corresponding chapter raw text
        try:
            ch = chapters[idx - 1]
            raw_text = ch.get("raw_text", "") if isinstance(ch, dict) else ""
        except Exception:
            raw_text = ""

        # compute extracted chunk count from checkpoint state when available
        extracted_chunks = 0
        try:
            chapter_id = None
            if isinstance(ch, dict):
                chapter_id = ch.get("chapter_id") or sha(ch.get("raw_text", ""))
            if chapter_id:
                chapter_key = f"chapter_{chapter_id}"
                chap_state = chunks_state.get(chapter_key, {})
                extracted_chunks = len(chap_state.get("completed", {}) or {})
        except Exception:
            extracted_chunks = 0

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

    with open(os.path.join(storage, "02_doctrine.json"), "w", encoding="utf-8") as f:
        json.dump(doctrines, f, indent=2, ensure_ascii=False)

    # Phase 2.5: build minister memories (atomic AKUs -> per-minister stores)
    try:
        live_progress(storage, phase="phase_2.5", message="Building minister memories")
        # write minister memories into Sovereign/data/memory by default
        ministers_storage = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "memory"))
        os.makedirs(ministers_storage, exist_ok=True)
        # provide a progress callback so minister building reports into live progress
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

    # Fail only if every chapter failed to produce doctrine
    if len(errors) == total:
        raise RuntimeError("All chapters failed — aborting ingest")
    if errors:
        print(f"[INGEST] Completed with {len(errors)} partial chapter warnings")

    live_progress(storage, phase="phase_2", message="Doctrine extraction completed", current=total, total=total)

    # ============================================================
    # Phase 3 	6 Embeddings + Index
    # ============================================================
    live_progress(storage, phase="phase_3", message="Embedding started")
    nodes = []
    def normalize_doctrine(d: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(d)
        # normalize principles
        p_out = []
        for p in out.get("principles", []) or []:
            if isinstance(p, str):
                p_out.append({"id": sha(p), "statement": p, "abstracted_from": None})
            elif isinstance(p, dict):
                p_out.append(p)
        out["principles"] = p_out

        # normalize rules
        r_out = []
        for r in out.get("rules", []) or []:
            if isinstance(r, str):
                # try to parse IF/THEN
                s = r
                parts = re.split(r"\bTHEN\b", s, flags=re.IGNORECASE)
                if len(parts) == 2:
                    cond = parts[0].strip()
                    act = parts[1].strip()
                else:
                    cond = ""
                    act = s
                r_out.append({"condition": cond, "action": act})
            elif isinstance(r, dict):
                r_out.append(r)
        out["rules"] = r_out

        # normalize claims
        c_out = []
        for c in out.get("claims", []) or []:
            if isinstance(c, str):
                c_out.append({"claim": c, "confidence": None})
            elif isinstance(c, dict):
                c_out.append(c)
        out["claims"] = c_out

        # normalize warnings
        w_out = []
        for w in out.get("warnings", []) or []:
            if isinstance(w, str):
                w_out.append({"situation": w, "risk": None})
            elif isinstance(w, dict):
                w_out.append(w)
        out["warnings"] = w_out

        return out

    for d in doctrines:
        nd = normalize_doctrine(d)
        nodes.extend(doctrine_to_nodes(nd, prefix=book_id.upper()))
    # Only embed principles, rules, claims (exclude warnings and raw blobs)
    nodes_to_embed = [n for n in nodes if n.get("type") in ("principle", "rule", "claim")]

    # Parallel-safe embedding with live progress updates
    embeddings = []
    total_nodes = len(nodes_to_embed)
    if total_nodes > 0:
        completed = 0
        live_progress(storage, phase="phase_3", message="Embedding doctrine nodes", current=0, total=total_nodes)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            future_to_node = {ex.submit(extractor_client.embed, n.get("text")): n for n in nodes_to_embed}
            for fut in as_completed(future_to_node):
                n = future_to_node[fut]
                try:
                    vec = fut.result()
                except Exception as e:
                    vec = None
                    try:
                        with open(os.path.join(storage, "03_embeddings_errors.log"), "a", encoding="utf-8") as ef:
                            ef.write(f"Embedding error for node {n.get('node_id')}: {e}\n")
                    except Exception:
                        pass

                if vec:
                    embeddings.append({
                        "embedding_id": f"emb-{n['node_id']}",
                        "node_id": n["node_id"],
                        "node_type": n["type"],
                        "text": n.get("text"),
                        "vector": vec,
                        "metadata": n.get("metadata", {}),
                    })

                completed += 1
                try:
                    live_progress(storage, phase="phase_3", message="Embedding doctrine nodes", current=completed, total=total_nodes)
                except Exception:
                    pass

    try:
        with open(os.path.join(storage, "03_embeddings.json"), "w", encoding="utf-8") as f:
            json.dump(embeddings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Final overall progress marker and friendly terminal confirmation
    live_progress(storage, phase="completed", message="Ingestion finished", current=100, total=100)
    print("[INGEST] Completed successfully")


# ============================================================
# ENTRYPOINT
# ============================================================

def ingest_folder(folder_path: str, *, fresh: bool = False):
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
            run_full_ingest_with_resume(
                pdf,
                resume=not fresh
            )
        except Exception as e:
            print(f"[INGEST][ERROR] {pdf}: {e}")


if __name__ == "__main__":
    import argparse
    import os

    print("[BOOT] CLI entry reached", flush=True)

    parser = argparse.ArgumentParser(description="RAG ingest runner")
    parser.add_argument(
        "path",
        help="Path to a PDF file OR a folder containing PDFs"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore existing RAG data and re-ingest"
    )

    args = parser.parse_args()

    print(f"[BOOT] args = {args}", flush=True)

    if os.path.isdir(args.path):
        print(f"[INGEST] Folder mode: {args.path}", flush=True)
        ingest_folder(args.path, fresh=args.fresh)
    else:
        print(f"[INGEST] File mode: {args.path}", flush=True)
        run_full_ingest_with_resume(
            args.path,
            resume=not args.fresh
        )