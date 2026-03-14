"""Helpers for selecting and weighting experts."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(float(value) for value in weights.values())
    if total <= 0.0:
        return {name: 0.0 for name in weights}
    return {name: round(float(value) / total, 4) for name, value in weights.items()}


def select_top_k(weights: Dict[str, float], k: int) -> Dict[str, float]:
    if not weights:
        return {}
    k = max(1, int(k))
    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:k]
    return normalize_weights(dict(ranked))


def aggregate_scores(
    expert_scores: Iterable[Tuple[str, float]], weights: Dict[str, float]
) -> float:
    total = 0.0
    for name, score in expert_scores:
        total += float(score) * float(weights.get(name, 0.0))
    return total
