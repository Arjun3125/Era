"""Reasoning rubric evaluation for ERA outputs."""

from __future__ import annotations

from typing import Iterable


def rubric_score(reasoning: str, rubric: Iterable[str]) -> float:
    items = [str(item).strip().lower() for item in rubric if str(item).strip()]
    if not items:
        return 0.0
    text = str(reasoning or "").lower()
    hits = sum(1 for item in items if item in text)
    return round(hits / len(items), 4)
