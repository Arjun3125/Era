"""Bootstrap statistics for experiment metrics."""

from __future__ import annotations

import random
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
