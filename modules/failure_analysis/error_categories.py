"""Failure categorization heuristics for ERA decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping


@dataclass(frozen=True)
class FailureCategoryConfig:
    policy_confidence_threshold: float = 0.7
    value_margin: float = 0.05
    consensus_threshold: float = 0.3
    overconfidence_threshold: float = 0.7
    high_budget_threshold: int = 2
    low_uncertainty_threshold: float = 0.2


def _normalize_key(value: str) -> str:
    return str(value or "").strip().lower()


def _max_score(scores: Mapping[str, float] | None) -> tuple[str, float]:
    if not scores:
        return "", 0.0
    best = max(scores.items(), key=lambda item: float(item[1]))
    return str(best[0]), float(best[1])


def classify_failure(trace: Mapping[str, object], config: FailureCategoryConfig | None = None) -> List[str]:
    cfg = config or FailureCategoryConfig()
    categories: List[str] = []

    decision = _normalize_key(trace.get("model_decision", ""))
    expected = _normalize_key(trace.get("expected_decision", ""))
    if decision == expected:
        return categories

    policy_scores = trace.get("policy_probabilities") or {}
    value_scores = trace.get("value_scores") or {}
    council_signal = trace.get("council_signal") or {}

    policy_top, policy_top_score = _max_score(policy_scores if isinstance(policy_scores, Mapping) else {})
    value_top, _ = _max_score(value_scores if isinstance(value_scores, Mapping) else {})

    if policy_top_score >= cfg.policy_confidence_threshold and decision == _normalize_key(policy_top):
        categories.append("policy_overconfidence")

    if isinstance(value_scores, Mapping) and expected in value_scores and decision in value_scores:
        expected_value = float(value_scores.get(expected, 0.0))
        chosen_value = float(value_scores.get(decision, 0.0))
        if expected_value > chosen_value + cfg.value_margin:
            categories.append("value_misprediction")

    if isinstance(council_signal, Mapping):
        consensus = float(council_signal.get("consensus_strength", 0.0))
        if consensus <= cfg.consensus_threshold:
            categories.append("council_disagreement")

    confidence = float(trace.get("confidence", 0.0) or 0.0)
    if confidence >= cfg.overconfidence_threshold:
        categories.append("uncertainty_overconfidence")

    budget = int(trace.get("budget", trace.get("reasoning_budget", 0)) or 0)
    policy_entropy = float(trace.get("policy_entropy", 0.0) or 0.0)
    value_variance = float(trace.get("value_variance", 0.0) or 0.0)
    if budget >= cfg.high_budget_threshold and policy_entropy < cfg.low_uncertainty_threshold and value_variance < cfg.low_uncertainty_threshold:
        categories.append("controller_budget_error")

    if policy_top and value_top and _normalize_key(policy_top) != _normalize_key(value_top):
        categories.append("policy_value_conflict")

    return categories or ["unknown"]
