"""Doctrine extraction stub for v2 ingestion pipeline."""
from __future__ import annotations

from typing import Dict, Any, List


def extract_doctrine(
    chapter: Dict[str, Any],
    *,
    client=None,
    book_title: str = "",
    chapter_index: int | None = None,
    chapter_title: str | None = None,
    storage: str | None = None,
    **_kwargs,
) -> Dict[str, Any]:
    """
    Minimal doctrine extraction placeholder.
    Produces a valid doctrine shape without LLM calls.
    """
    idx = chapter_index or chapter.get("chapter_index") or 1
    title = chapter_title or chapter.get("chapter_title") or f"{book_title or 'Book'} Chapter {idx}"
    text = chapter.get("raw_text") or chapter.get("text") or ""

    # Lightweight heuristic: mark domains if keywords appear.
    lower = text.lower()
    domains: List[str] = []
    if "risk" in lower:
        domains.append("risk")
    if "strategy" in lower or "plan" in lower:
        domains.append("strategy")
    if not domains:
        domains = ["strategy"]

    return {
        "chapter_index": idx,
        "chapter_title": title,
        "domains": domains,
        "principles": [],
        "rules": [],
        "claims": [],
        "warnings": [],
    }
