"""Accuracy and aggregate metrics for ERA evaluation."""

from __future__ import annotations

from typing import Iterable, List


def accuracy_score(predicted: str, expected: str) -> int:
    return int(str(predicted).strip().lower() == str(expected).strip().lower())


def average(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def clamp_score(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def normalize_scores(values: Iterable[float]) -> List[float]:
    return [clamp_score(float(value)) for value in values]
