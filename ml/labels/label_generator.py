"""Generate training labels for ML Judgment Prior.

Outputs lightweight, bounded type weights so the learning system stays
interpretable and stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


def _clamp(value: float, low: float = 0.7, high: float = 1.3) -> float:
    return max(low, min(high, value))


@dataclass
class TypeWeights:
    principle_weight: float = 1.0
    rule_weight: float = 1.0
    warning_weight: float = 1.0
    claim_weight: float = 1.0
    advice_weight: float = 1.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "principle_weight": float(self.principle_weight),
            "rule_weight": float(self.rule_weight),
            "warning_weight": float(self.warning_weight),
            "claim_weight": float(self.claim_weight),
            "advice_weight": float(self.advice_weight),
        }


def generate_type_weights(
    situation_features: Dict[str, float],
    constraint_features: Dict[str, float],
    kis_features: Dict[str, float],
    outcome: Dict[str, Any],
) -> TypeWeights:
    """Create bounded weights from outcome signals."""
    success = bool(outcome.get("success", False))
    regret = float(outcome.get("regret_score", 0.0) or 0.0)

    # Risk proxy from constraints (prefer irreversibility/fragility if present).
    risk_signal = max(
        float(constraint_features.get("irreversibility_score", 0.0) or 0.0),
        float(constraint_features.get("fragility_score", 0.0) or 0.0),
    )

    base = 1.05 if success else 0.95
    regret_penalty = 0.2 * regret

    principle = _clamp(base - regret_penalty)
    rule = _clamp(base - regret_penalty * 0.8)
    warning = _clamp(1.0 + 0.15 * risk_signal - regret_penalty)
    claim = _clamp(base - regret_penalty * 0.6)
    advice = _clamp(base - regret_penalty * 0.5)

    return TypeWeights(
        principle_weight=principle,
        rule_weight=rule,
        warning_weight=warning,
        claim_weight=claim,
        advice_weight=advice,
    )
