"""Decision regret metrics for ERA evaluation."""

from __future__ import annotations

from typing import Dict


def regret_score(option_scores: Dict[str, float], chosen: str) -> float:
    if not option_scores:
        return 0.0
    best = max(option_scores.values())
    chosen_score = option_scores.get(chosen, best)
    return round(best - chosen_score, 4)
