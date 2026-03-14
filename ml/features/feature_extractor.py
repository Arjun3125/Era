"""Lightweight feature extraction for the ML Wisdom System.

This module intentionally stays simple and stable. It provides dataclass
structures that align with the LLM handshake outputs and a single helper
to convert those structures (or dicts) into numeric feature vectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


@dataclass
class SituationState:
    decision_type: str = "exploratory"  # irreversible | reversible | exploratory
    risk_level: str = "medium"  # low | medium | high
    time_horizon: str = "medium"  # short | medium | long
    time_pressure: float = 0.5
    information_completeness: float = 0.5
    agency: str = "individual"  # individual | org
    confidence: float = 0.5


@dataclass
class ConstraintState:
    irreversibility_score: float = 0.5
    fragility_score: float = 0.5
    optionality_loss_score: float = 0.5
    downside_asymmetry: float = 0.5
    upside_asymmetry: float = 0.5
    likely_regret_if_wrong: float = 0.5
    confidence: float = 0.5


@dataclass
class KISOutput:
    knowledge_trace: Iterable[Any]
    used_principle: bool
    used_rule: bool
    used_warning: bool
    used_claim: bool
    used_advice: bool
    avg_kis_principle: float = 0.0
    avg_kis_rule: float = 0.0
    avg_kis_warning: float = 0.0
    avg_kis_claim: float = 0.0
    avg_kis_advice: float = 0.0
    num_entries_used: int = 0
    avg_entry_age_days: float = 0.0
    avg_penalty_count: float = 0.0


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _one_hot(prefix: str, value: str, choices: Iterable[str]) -> Dict[str, float]:
    return {f"{prefix}_{c}": float(value == c) for c in choices}


def build_feature_vector(
    situation: SituationState | Dict[str, Any] | None,
    constraints: ConstraintState | Dict[str, Any] | None,
    kis: KISOutput | Dict[str, Any] | None = None,
) -> Dict[str, float]:
    """Convert inputs into a flat numeric feature map."""
    features: Dict[str, float] = {}

    if situation is not None:
        decision_type = _get(situation, "decision_type", "exploratory")
        risk_level = _get(situation, "risk_level", "medium")
        time_horizon = _get(situation, "time_horizon", "medium")
        agency = _get(situation, "agency", "individual")

        features.update(_one_hot("decision", decision_type, ["irreversible", "reversible", "exploratory"]))
        features.update(_one_hot("risk", risk_level, ["low", "medium", "high"]))
        features.update(_one_hot("horizon", time_horizon, ["short", "medium", "long"]))
        features.update(_one_hot("agency", agency, ["individual", "org"]))

        features["time_pressure"] = float(_get(situation, "time_pressure", 0.5))
        features["information_completeness"] = float(_get(situation, "information_completeness", 0.5))
        features["situation_confidence"] = float(_get(situation, "confidence", 0.5))

    if constraints is not None:
        features["irreversibility_score"] = float(_get(constraints, "irreversibility_score", 0.5))
        features["fragility_score"] = float(_get(constraints, "fragility_score", 0.5))
        features["optionality_loss_score"] = float(_get(constraints, "optionality_loss_score", 0.5))
        features["downside_asymmetry"] = float(_get(constraints, "downside_asymmetry", 0.5))
        features["upside_asymmetry"] = float(_get(constraints, "upside_asymmetry", 0.5))
        features["likely_regret_if_wrong"] = float(_get(constraints, "likely_regret_if_wrong", 0.5))
        features["constraint_confidence"] = float(_get(constraints, "confidence", 0.5))

    if kis is not None:
        features["used_principle"] = float(_get(kis, "used_principle", False))
        features["used_rule"] = float(_get(kis, "used_rule", False))
        features["used_warning"] = float(_get(kis, "used_warning", False))
        features["used_claim"] = float(_get(kis, "used_claim", False))
        features["used_advice"] = float(_get(kis, "used_advice", False))
        features["avg_kis_principle"] = float(_get(kis, "avg_kis_principle", 0.0))
        features["avg_kis_rule"] = float(_get(kis, "avg_kis_rule", 0.0))
        features["avg_kis_warning"] = float(_get(kis, "avg_kis_warning", 0.0))
        features["avg_kis_claim"] = float(_get(kis, "avg_kis_claim", 0.0))
        features["avg_kis_advice"] = float(_get(kis, "avg_kis_advice", 0.0))
        features["num_entries_used"] = float(_get(kis, "num_entries_used", 0.0))
        features["avg_entry_age_days"] = float(_get(kis, "avg_entry_age_days", 0.0))
        features["avg_penalty_count"] = float(_get(kis, "avg_penalty_count", 0.0))

    return features
