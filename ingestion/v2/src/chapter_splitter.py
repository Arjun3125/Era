"""Chapter splitting helpers for v2 ingestion (compat shim)."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Union


def fallback_split_by_headings(pages: Union[List[str], str], book_title: str = "") -> List[Dict[str, Any]]:
    """Fallback split using heading heuristics for tests."""
    if not pages:
        return []

    text = "\n".join(pages) if isinstance(pages, list) else str(pages)
    headings = re.split(r"\n(?=[A-Z][A-Z\s]{3,}:?)", text)
    chapters: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(headings, start=1):
        chunk = chunk.strip()
        if not chunk:
            continue
        title_line = chunk.splitlines()[0].strip() if chunk.splitlines() else f"Chapter {idx}"
        chapters.append(
            {
                "chapter_index": idx,
                "chapter_title": title_line[:80],
                "raw_text": chunk,
            }
        )
    if len(chapters) <= 1 and len(text) > 5000:
        chapters = []
        chunk_size = 15000
        for idx, i in enumerate(range(0, len(text), chunk_size), start=1):
            chunk = text[i:i+chunk_size].strip()
            if chunk:
                chapters.append({
                    "chapter_index": idx,
                    "chapter_title": f"Chapter {idx}",
                    "raw_text": chunk,
                })
    elif len(chapters) == 0 and text.strip():
        chapters = [{
            "chapter_index": 1,
            "chapter_title": book_title or "Chapter 1",
            "raw_text": text.strip(),
        }]
    return chapters


def split_chapters_with_ollama_streaming(
    pages: List[str],
    client=None,
    book_title: str = "",
    storage: str = "",
) -> List[Dict[str, Any]]:
    """Split chapters using Ollama or fallback to heading heuristics."""
    try:
        from ingestion.v1.ingest import split_chapters_with_ollama_streaming as _split_v1
        return _split_v1(pages, client=client, book_title=book_title, storage=storage)
    except (ImportError, ModuleNotFoundError):
        print("[CHAPTER] v1 LLM splitter unavailable, using heading heuristics")
        return fallback_split_by_headings(pages, book_title=book_title)
