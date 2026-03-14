"""Chapter splitting helpers for v2 ingestion (compat shim)."""
from __future__ import annotations

import re
from typing import List, Dict, Any

from ingestion.v1.ingest import split_chapters_with_ollama_streaming as _split_v1


def split_chapters_with_ollama_streaming(
    pages: List[str],
    client=None,
    book_title: str = "",
    storage: str = "",
) -> List[Dict[str, Any]]:
    """Reuse v1 stub split for test coverage."""
    return _split_v1(pages, client=client, book_title=book_title, storage=storage)


def fallback_split_by_headings(pages: List[str]) -> List[Dict[str, Any]]:
    """Fallback split using heading heuristics for tests."""
    if not pages:
        return []

    text = "\n".join(pages)
    headings = re.split(r"\n(?=[A-Z][A-Z\\s]{3,}:?)", text)
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
    return chapters
