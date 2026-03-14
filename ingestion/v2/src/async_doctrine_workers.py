"""Async doctrine extraction stub for v2 ingestion."""
from __future__ import annotations

from typing import Any, Dict, List

from .doctrine_extractor import extract_doctrine


async def run_async_doctrine_extraction(
    chapters: List[Dict[str, Any]],
    *,
    client=None,
    book_title: str = "",
    storage: str = "",
    **_kwargs,
) -> List[Dict[str, Any]]:
    """Sequential async-compatible extractor (no concurrency)."""
    results: List[Dict[str, Any]] = []
    for idx, chapter in enumerate(chapters, start=1):
        results.append(
            extract_doctrine(
                chapter,
                client=client,
                book_title=book_title,
                chapter_index=idx,
                chapter_title=chapter.get("chapter_title"),
                storage=storage,
            )
        )
    return results
