"""Helpers for building and persisting decision traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from modules.evaluation_engine.budget_metrics import ComputeCostConfig, compute_cost, compute_quality


def _normalize_scores(scores: Mapping[str, float] | None) -> Dict[str, float]:
    if not scores:
        return {}
    total = sum(float(value) for value in scores.values())
    if total <= 0:
        return {str(k): float(v) for k, v in scores.items()}
    return {str(k): float(v) / total for k, v in scores.items()}


def build_trace(
    *,
    scenario: Mapping[str, Any],
    result: Mapping[str, Any],
    cost_config: ComputeCostConfig | None = None,
) -> Dict[str, Any]:
    era = result.get("era", {}) if isinstance(result, Mapping) else {}
    cost_cfg = cost_config or ComputeCostConfig()

    decision = str(era.get("decision", "")).strip().lower()
    expected = str(result.get("expected_decision", "")).strip().lower()

    policy_scores = era.get("option_policy_scores", {}) or {}
    value_scores = era.get("option_value_scores", {}) or {}
    council_metrics = era.get("council_metrics", {}) or {}

    budget = int(era.get("reasoning_budget", 0) or 0)
    minister_count = int(era.get("minister_count", 0) or 0)
    decision_correct = float(era.get("decision_correct", 0.0))
    regret = float(era.get("regret", 0.0))
    rubric_score = float(era.get("rubric_score", 0.0))
    quality = compute_quality(decision_correct, regret, rubric_score)
    compute_cost_value = compute_cost(budget, minister_count, cost_cfg)

    return {
        "scenario_id": str(result.get("scenario_id", "")),
        "category": result.get("category"),
        "difficulty": result.get("difficulty"),
        "prompt": scenario.get("prompt", ""),
        "context": scenario.get("context", {}),
        "expected_decision": expected,
        "model_decision": decision,
        "decision_correct": decision_correct,
        "policy_probabilities": _normalize_scores(policy_scores),
        "value_scores": {str(k): float(v) for k, v in value_scores.items()} if isinstance(value_scores, Mapping) else {},
        "council_signal": council_metrics,
        "budget": budget,
        "minister_count": minister_count,
        "confidence": float(era.get("confidence", 0.0)),
        "confidence_calibrated": float(era.get("confidence_calibrated", 0.0)),
        "risk_score": float(era.get("risk_score", 0.0)),
        "policy_entropy": float(era.get("policy_entropy", 0.0)),
        "value_variance": float(era.get("value_variance", 0.0)),
        "regret": regret,
        "rubric_score": rubric_score,
        "quality": quality,
        "compute_cost": compute_cost_value,
        "utility": quality - compute_cost_value,
        "option_scores": era.get("option_scores", {}),
        "option_hybrid_all_scores": era.get("option_hybrid_all_scores", {}),
    }


def write_traces(path: Path, traces: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for trace in traces:
            handle.write(json.dumps(trace, ensure_ascii=True))
            handle.write("\n")
