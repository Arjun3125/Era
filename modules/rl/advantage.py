"""Advantage estimation (GAE) utilities."""

from __future__ import annotations

from typing import Iterable, List, Tuple


def compute_advantages(
    rewards: Iterable[float],
    values: Iterable[float],
    dones: Iterable[bool],
    *,
    gamma: float = 0.99,
    lam: float = 0.95,
) -> List[float]:
    rewards_list = list(rewards)
    values_list = list(values)
    dones_list = list(dones)
    if len(values_list) == len(rewards_list):
        values_list.append(0.0)

    advantages: List[float] = []
    gae = 0.0
    for t in reversed(range(len(rewards_list))):
        mask = 0.0 if dones_list[t] else 1.0
        delta = rewards_list[t] + gamma * values_list[t + 1] * mask - values_list[t]
        gae = delta + gamma * lam * mask * gae
        advantages.insert(0, gae)
    return advantages


def compute_returns(values: Iterable[float], advantages: Iterable[float]) -> List[float]:
    return [float(v) + float(a) for v, a in zip(values, advantages)]
