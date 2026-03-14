"""Bootstrap and comparative statistics for experiment metrics."""

from __future__ import annotations

import math
import random
from statistics import mean, pstdev
from typing import Iterable, List, Tuple


def bootstrap_ci(values: Iterable[float], *, n: int = 1000, seed: int = 42) -> Tuple[float, float]:
    items = list(values)
    if not items:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(n):
        sample = [rng.choice(items) for _ in range(len(items))]
        means.append(sum(sample) / len(sample))
    means.sort()
    lower = means[int(0.025 * (n - 1))]
    upper = means[int(0.975 * (n - 1))]
    return (round(lower, 4), round(upper, 4))


def mean_std(values: Iterable[float]) -> Tuple[float, float]:
    items = list(values)
    if not items:
        return (0.0, 0.0)
    return (round(mean(items), 4), round(pstdev(items), 4))


def paired_t_test(a: Iterable[float], b: Iterable[float]) -> Tuple[float, float]:
    items_a = list(a)
    items_b = list(b)
    if not items_a or not items_b or len(items_a) != len(items_b):
        return (0.0, 1.0)
    diffs = [x - y for x, y in zip(items_a, items_b)]
    avg = mean(diffs)
    sd = pstdev(diffs)
    if sd == 0:
        return (0.0, 1.0)
    t_stat = avg / (sd / math.sqrt(len(diffs)))
    # Normal approximation for large n.
    p_value = 2.0 * (1.0 - _normal_cdf(abs(t_stat)))
    return (round(t_stat, 4), round(p_value, 6))


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def effect_size(a: Iterable[float], b: Iterable[float]) -> float:
    items_a = list(a)
    items_b = list(b)
    if not items_a or not items_b or len(items_a) != len(items_b):
        return 0.0
    diffs = [x - y for x, y in zip(items_a, items_b)]
    sd = pstdev(diffs)
    if sd == 0:
        return 0.0
    return round(mean(diffs) / sd, 4)
