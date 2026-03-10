"""Weighted aggregation of minister positions."""

from __future__ import annotations

from typing import Any, Dict, Tuple


_STANCE_SCORE = {
    "support": 1.0,
    "oppose": -1.0,
    "neutral": 0.0,
}


def aggregate_weighted_positions(
    minister_positions: Dict[str, Dict[str, Any]],
    expert_weights: Dict[str, float],
) -> Dict[str, Any]:
    weighted_score = 0.0
    weight_sum = 0.0
    support_weight = 0.0
    oppose_weight = 0.0
    neutral_weight = 0.0

    for minister, position in minister_positions.items():
        stance = str(position.get("stance", "neutral")).lower()
        confidence = float(position.get("confidence", 0.5) or 0.5)
        weight = float(expert_weights.get(minister, 0.0))
        score = _STANCE_SCORE.get(stance, 0.0) * confidence
        weighted_score += weight * score
        weight_sum += weight
        if stance == "support":
            support_weight += weight
        elif stance == "oppose":
            oppose_weight += weight
        else:
            neutral_weight += weight

    if weight_sum <= 0:
        return {
            "recommendation": "neutral",
            "weighted_score": 0.0,
            "consensus_strength": 0.0,
            "support_weight": 0.0,
            "oppose_weight": 0.0,
            "neutral_weight": 0.0,
        }

    normalized_score = weighted_score / weight_sum
    if normalized_score >= 0.15:
        recommendation = "support"
    elif normalized_score <= -0.15:
        recommendation = "oppose"
    else:
        recommendation = "neutral"

    return {
        "recommendation": recommendation,
        "weighted_score": round(normalized_score, 4),
        "consensus_strength": round(abs(normalized_score), 4),
        "support_weight": round(support_weight / weight_sum, 4),
        "oppose_weight": round(oppose_weight / weight_sum, 4),
        "neutral_weight": round(neutral_weight / weight_sum, 4),
    }
