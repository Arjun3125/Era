"""Chapter boundary detection and text segmentation."""
import json
import os
import re
from typing import List, Dict, Any, Optional

from .config import PHASE1_SYSTEM_PROMPT, CACHE_DIR
from .utils import sha
from .ollama_client import OllamaClient, call_json_llm_strict


def split_chapters_with_ollama_streaming(
    pages: List[str],
    *,
    client: OllamaClient,
    book_title: Optional[str] = None,
    storage: Optional[str] = None,
    progress_cb=None,
) -> List[Dict[str, Any]]:
    """
    Phase 1: Ollama-driven streaming chapter detection.
    Deterministic wrapper using LLM for boundary decisions.
    
    Args:
        pages: List of page texts
        client: OllamaClient instance
        book_title: Optional book title
        storage: Optional storage for progress tracking
        progress_cb: Optional progress callback
        
    Returns:
        List of chapter dicts with structure:
        {chapter_index, chapter_id, chapter_title, raw_text}
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
        # Emit progress
        if progress_cb:
            try:
                progress_cb(phase="phase_1", message=f"Chapter split: page {page_no}/{len(pages)}", 
                          current=page_no, total=len(pages))
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
            
            decision = None
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as cf:
                        decision = json.load(cf)
                except Exception:
                    pass
            
            if decision is None:
                decision = call_json_llm_strict(
                    prompt=user_prompt,
                    system=PHASE1_SYSTEM_PROMPT,
                    client=client,
                    timeout=120,
                )
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

    # flush final chapter
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


def fallback_split_by_headings(text: str) -> List[Dict[str, Any]]:
    """
    Fallback splitter using heading pattern detection.
    
    Looks for patterns like "THE FIRST BOOK", "BOOK I", "CHAPTER 1".
    Used when LLM-driven splitter produces single chapter for long text.
    
    Args:
        text: Full text to split
        
    Returns:
        List of chapter dicts
    """
    if not text or not text.strip():
        return []

    # candidate heading regexes
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

    # If no useful headings found, return single-chapter fallback
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