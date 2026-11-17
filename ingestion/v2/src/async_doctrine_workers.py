"""Async doctrine extraction for v2 ingestion with bounded concurrency."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from .doctrine_extractor import extract_doctrine


async def run_async_doctrine_extraction(
    chapters: List[Dict[str, Any]],
    *,
    client=None,
    book_title: str = "",
    storage: str = "",
    num_workers: int = 2,
    progress_cb: Optional[Callable] = None,
    **_kwargs,
) -> List[Dict[str, Any]]:
    """Concurrent async doctrine extractor using bounded semaphore."""
    if not chapters:
        return []

    semaphore = asyncio.Semaphore(max(1, int(num_workers)))

    async def _process_chapter(idx: int, chapter: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:
            try:
                res = await asyncio.to_thread(
                    extract_doctrine,
                    chapter,
                    client=client,
                    book_title=book_title,
                    chapter_index=idx,
                    chapter_title=chapter.get("chapter_title"),
                    storage=storage,
                    progress_cb=progress_cb,
                )
                return res
            except Exception as e:
                return {
                    "chapter_index": idx,
                    "chapter_title": chapter.get("chapter_title", f"Chapter {idx}"),
                    "domains": [],
                    "principles": [],
                    "rules": [],
                    "claims": [],
                    "warnings": [],
                    "_error": str(e),
                }

    tasks = [
        _process_chapter(idx, ch)
        for idx, ch in enumerate(chapters, start=1)
    ]
    return await asyncio.gather(*tasks)

