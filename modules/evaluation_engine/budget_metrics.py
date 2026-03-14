"""Compute budget efficiency metrics for adaptive reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

from .metrics import average


@dataclass(frozen=True)
class ComputeCostConfig:
    budget_weight: float = 0.5
    minister_weight: float = 0.2
    base_cost: float = 0.0


def compute_cost(budget: float, ministers_used: float, config: ComputeCostConfig) -> float:
    return max(
        0.0,
        config.base_cost + config.budget_weight * float(budget) + config.minister_weight * float(ministers_used),
    )


def compute_quality(decision_correct: float, regret: float, rubric_score: float) -> float:
    return float(decision_correct) - float(regret) + float(rubric_score)


def compute_efficiency(quality: float, cost: float) -> float:
    if cost <= 0.0:
        return 0.0
    return quality / cost


def aggregate_budget_metrics(
    results: Iterable[Mapping[str, object]],
    *,
    cost_config: ComputeCostConfig | None = None,
) -> Dict[str, object]:
    config = cost_config or ComputeCostConfig()
    by_budget: Dict[int, List[Dict[str, float]]] = {}
    overall: List[Dict[str, float]] = []

    for item in results:
        era = item.get("era", {}) if isinstance(item, Mapping) else {}
        if not isinstance(era, Mapping):
            continue
        budget_raw = era.get("reasoning_budget", 0)
        minister_raw = era.get("minister_count", 0)
        try:
            budget = int(budget_raw)
        except (TypeError, ValueError):
            budget = 0
        try:
            minister_count = float(minister_raw)
        except (TypeError, ValueError):
            minister_count = 0.0

        decision_correct = float(era.get("decision_correct", 0))
        regret = float(era.get("regret", 0.0))
        rubric_score = float(era.get("rubric_score", 0.0))

        quality = compute_quality(decision_correct, regret, rubric_score)
        cost = compute_cost(budget, minister_count, config)
        efficiency = compute_efficiency(quality, cost)

        record = {
            "quality": quality,
            "compute_cost": cost,
            "efficiency": efficiency,
            "decision_correct": decision_correct,
            "regret": regret,
            "rubric_score": rubric_score,
            "minister_count": minister_count,
            "budget": float(budget),
        }
        overall.append(record)
        by_budget.setdefault(budget, []).append(record)

    def _summarize(records: List[Dict[str, float]]) -> Dict[str, float]:
        return {
            "count": float(len(records)),
            "avg_quality": round(average(item["quality"] for item in records), 4),
            "avg_compute_cost": round(average(item["compute_cost"] for item in records), 4),
            "avg_efficiency": round(average(item["efficiency"] for item in records), 4),
            "avg_accuracy": round(average(item["decision_correct"] for item in records), 4),
            "avg_regret": round(average(item["regret"] for item in records), 4),
            "avg_rubric_score": round(average(item["rubric_score"] for item in records), 4),
            "avg_minister_count": round(average(item["minister_count"] for item in records), 4),
        }

    summary = {
        "cost_config": {
            "budget_weight": config.budget_weight,
            "minister_weight": config.minister_weight,
            "base_cost": config.base_cost,
        },
        "overall": _summarize(overall) if overall else {},
        "by_budget": {str(budget): _summarize(records) for budget, records in sorted(by_budget.items())},
    }
    return summary
