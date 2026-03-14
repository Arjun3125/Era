"""Generate training data for the reasoning controller."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.evaluation_engine.runner import EvaluationRunner, load_scenarios
from modules.evaluation_engine.budget_metrics import ComputeCostConfig, compute_cost, compute_quality


def budget_overrides(budget: int, *, router_path: str | None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"reasoning_budget": budget}
    if budget <= 0:
        payload.update({"disable_ministers": True, "requested_mode": "quick"})
        return payload
    if budget == 1:
        payload.update({
            "requested_mode": "meeting",
            "expert_router_enabled": True,
            "expert_router_top_k": 2,
        })
        if router_path:
            payload["expert_router_path"] = router_path
        return payload
    if budget == 2:
        payload.update({
            "requested_mode": "meeting",
            "expert_router_enabled": True,
            "expert_router_top_k": 4,
        })
        if router_path:
            payload["expert_router_path"] = router_path
        return payload
    payload["requested_mode"] = "darbar"
    return payload


def _policy_entropy(scores: Dict[str, float]) -> float:
    if not scores:
        return 0.0
    values = [max(0.0, float(value)) for value in scores.values()]
    total = sum(values)
    if total <= 0:
        return 0.0
    probs = [value / total for value in values if value > 0]
    if not probs:
        return 0.0
    entropy = -sum(p * math.log(p + 1e-12) for p in probs)
    max_entropy = math.log(len(probs)) if len(probs) > 1 else 1.0
    return round(entropy / max_entropy if max_entropy > 0 else 0.0, 4)


def _value_variance(scores: Dict[str, float]) -> float:
    if not scores:
        return 0.0
    values = [float(value) for value in scores.values()]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return round(variance, 4)




def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reasoning controller training data.")
    parser.add_argument("--benchmark", default="era_benchmark")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--budgets", default="0,1,2,3")
    parser.add_argument("--output", default="data/reasoning_controller/runs_v1.jsonl")
    parser.add_argument("--policy-model", default=None)
    parser.add_argument("--value-model", default=None)
    parser.add_argument("--decision-policy", default="hybrid_all")
    parser.add_argument("--router-path", default=None)
    parser.add_argument("--probe-minister", default=None)
    parser.add_argument("--probe-label", default=None)
    parser.add_argument("--compute-penalty", type=float, default=0.1)
    parser.add_argument("--budget-weight", type=float, default=0.5)
    parser.add_argument("--minister-weight", type=float, default=0.2)
    parser.add_argument("--base-cost", type=float, default=0.0)
    args = parser.parse_args()

    budgets = [int(part.strip()) for part in str(args.budgets).split(",") if part.strip()]
    scenarios = load_scenarios(Path(args.benchmark), limit=args.limit)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scenario_map = {scenario.get("scenario_id"): scenario for scenario in scenarios}
    cost_config = ComputeCostConfig(
        budget_weight=args.budget_weight,
        minister_weight=args.minister_weight,
        base_cost=args.base_cost,
    )

    with output_path.open("w", encoding="utf-8") as handle:
        for budget in budgets:
            routing_context = budget_overrides(budget, router_path=args.router_path)
            if args.probe_minister:
                routing_context["probe_minister"] = args.probe_minister
            if args.probe_label:
                routing_context["probe_label"] = args.probe_label
            runner = EvaluationRunner(
                scenarios,
                decision_policy=args.decision_policy,
                policy_model_path=args.policy_model,
                value_model_path=args.value_model,
                routing_context=routing_context,
            )
            summary = runner.run()
            for result in summary.get("results", []):
                scenario_id = result.get("scenario_id", "")
                scenario = scenario_map.get(scenario_id, {})
                era = result.get("era", {})
                policy_scores = era.get("option_policy_scores", {}) or {}
                value_scores = era.get("option_value_scores", {}) or {}
                probe_metrics = era.get("probe_metrics", {}) or {}
                minister_count = int(era.get("minister_count", 0))
                decision_correct = float(era.get("decision_correct", 0.0))
                regret = float(era.get("regret", 0.0))
                rubric_score = float(era.get("rubric_score", 0.0))
                signals = {
                    "policy_entropy": _policy_entropy(policy_scores),
                    "value_variance": _value_variance(value_scores),
                    "minister_disagreement": probe_metrics.get("minister_disagreement", 0.0),
                    "risk_score": era.get("risk_score", 0.0),
                }
                quality = compute_quality(decision_correct, regret, rubric_score)
                cost = compute_cost(budget, minister_count, cost_config)
                utility = quality - float(args.compute_penalty) * cost
                row = {
                    "scenario_id": scenario_id,
                    "prompt": scenario.get("prompt", ""),
                    "context": scenario.get("context", {}),
                    "budget": budget,
                    "score": era.get("score", 0.0),
                    "decision_correct": decision_correct,
                    "regret": regret,
                    "rubric_score": rubric_score,
                    "quality": quality,
                    "compute_cost": cost,
                    "utility": utility,
                    "minister_count": minister_count,
                    "signals": signals,
                }
                handle.write(json.dumps(row, ensure_ascii=True))
                handle.write("\n")


if __name__ == "__main__":
    main()
