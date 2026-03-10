"""Benchmark runner for ERA-Bench scenarios."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.decision_pipeline import DecisionPipelineEngine


def build_option_prompt(base_prompt: str, option_text: str) -> str:
    return "\n".join(
        [
            "You are evaluating a single candidate decision option.",
            base_prompt.strip(),
            "",
            f"Candidate option under review: {option_text}",
            "",
            "Judge whether this option should be accepted, accepted with mitigation, deferred, or rejected.",
            "Prefer survivability, downside control, and strategic robustness over shallow optimism.",
        ]
    )


def score_option(result: Any) -> float:
    decision = str(getattr(result.decision_contract, "decision", "") or "").strip().lower()
    confidence = float(getattr(result.decision_contract, "confidence", 0.0) or 0.0)
    recommendation = str(
        getattr(result.decision_packaging_contract, "recommendation", "") or ""
    ).strip().lower()
    red_line_count = int(getattr(result.decision_packaging_contract, "red_line_count", 0) or 0)
    requires_followup = bool(
        getattr(result.decision_packaging_contract, "requires_followup", False)
    )

    base_scores = {
        "accept": 1.0,
        "accept_with_mitigation": 0.65,
        "direct_response": 0.35,
        "defer": 0.0,
        "reject": -1.0,
    }
    score = base_scores.get(decision, 0.0)
    score += max(0.0, min(1.0, confidence))
    if recommendation == "support":
        score += 0.15
    elif recommendation == "oppose":
        score -= 0.15
    score -= red_line_count * 0.2
    if requires_followup:
        score -= 0.1
    return round(score, 4)


def load_scenarios(root: Path, *, category: str | None = None, limit: int | None = None) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    categories = [category] if category else [p.name for p in (root / "scenarios").iterdir() if p.is_dir()]
    for cat in sorted(categories):
        for path in sorted((root / "scenarios" / cat).glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            scenarios.append(data)
            if limit and len(scenarios) >= limit:
                return scenarios
    return scenarios


def extract_reasoning(result: Any) -> str:
    # Prefer packaged decision rationale, then decision contract rationale.
    final_decision = getattr(result, "final_decision", {}) or {}
    contract = getattr(result, "decision_contract", None)
    rationale = ""
    if isinstance(final_decision, Mapping):
        rationale = str(final_decision.get("reason", "")).strip()
    if not rationale and contract:
        rationale = str(getattr(contract, "rationale", "")).strip()
    # Append knowledge trace snippets if available.
    knowledge_result = getattr(result, "knowledge_result", {}) or getattr(result, "knowledge_contract", {}) or {}
    synthesized = knowledge_result.get("synthesized_items") or knowledge_result.get("synthesized_knowledge") or []
    if isinstance(synthesized, Iterable) and not isinstance(synthesized, (str, bytes, bytearray)):
        rationale = f"{rationale} {' '.join(map(str, synthesized))}".strip()
    return rationale.lower()


def evaluate_decision(chosen_option: str, reasoning_text: str, scenario: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    decision = str(chosen_option or "").strip().lower()
    expected_decision = str(scenario.get("expected_decision", "")).strip().lower()
    decision_score = 1.0 if decision == expected_decision else 0.0

    rubric = scenario.get("reasoning_rubric") or []
    rubric_hits = 0
    for item in rubric:
        text = str(item).strip().lower()
        if text and text in reasoning_text:
            rubric_hits += 1
    reasoning_score = rubric_hits / len(rubric) if rubric else 0.0

    eval_weights = scenario.get("evaluation") or {}
    w_decision = float(eval_weights.get("decision_weight", 0.5))
    w_reason = float(eval_weights.get("reasoning_weight", 0.5))
    # Normalize weights if they don't sum to 1.
    total_w = w_decision + w_reason
    if not math.isclose(total_w, 1.0) and total_w > 0:
        w_decision /= total_w
        w_reason /= total_w

    score = w_decision * decision_score + w_reason * reasoning_score
    details = {
        "decision": decision,
        "expected_decision": expected_decision,
        "decision_score": decision_score,
        "reasoning_score": reasoning_score,
        "rubric_hits": rubric_hits,
        "rubric_total": len(rubric),
        "weights": {"decision": w_decision, "reasoning": w_reason},
    }
    return score, details


def run_benchmark(
    *,
    scenarios_root: Path,
    limit: int | None = None,
    category: str | None = None,
    requested_mode: str | None = None,
) -> Dict[str, Any]:
    pipeline = DecisionPipelineEngine.create()
    scenarios = load_scenarios(scenarios_root, category=category, limit=limit)
    scores: List[float] = []
    per_category: Dict[str, List[float]] = {}
    per_scenario_details: List[Dict[str, Any]] = []

    for scenario in scenarios:
        cat = scenario.get("category", "uncategorized")
        options = scenario.get("decision_options") or []
        best = None
        best_result = None
        option_scores: List[Dict[str, Any]] = []
        for option_text in options:
            result = pipeline.run(
                user_input=build_option_prompt(scenario["prompt"], option_text),
                requested_mode=requested_mode or scenario.get("mode") or "meeting",
                metadata={
                    "scenario_id": scenario.get("scenario_id"),
                    "benchmark": "era_bench",
                    "candidate_option": option_text,
                },
                source="era_benchmark",
            )
            score_value = score_option(result)
            option_scores.append(
                {
                    "option": option_text,
                    "score": score_value,
                    "confidence": float(getattr(result.decision_contract, "confidence", 0.0) or 0.0),
                    "decision": str(getattr(result.decision_contract, "decision", "") or "").strip().lower(),
                }
            )
            key = (score_value, float(getattr(result.decision_contract, "confidence", 0.0) or 0.0))
            if best is None or key > best:
                best = key
                best_result = (option_text, result)

        if best_result is None:
            chosen_option = ""
            reasoning_text = ""
        else:
            chosen_option, chosen_result = best_result
            reasoning_text = extract_reasoning(chosen_result)

        score, details = evaluate_decision(chosen_option, reasoning_text, scenario)
        scores.append(score)
        per_category.setdefault(cat, []).append(score)
        per_scenario_details.append(
            {
                "scenario_id": scenario.get("scenario_id"),
                "category": cat,
                "difficulty": scenario.get("difficulty"),
                "chosen_option": chosen_option,
                "option_scores": option_scores,
                "score": score,
                **details,
            }
        )

    summary = {
        "scenario_count": len(scenarios),
        "average_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "category_scores": {
            cat: round(sum(vals) / len(vals), 4) for cat, vals in sorted(per_category.items())
        },
        "per_scenario": per_scenario_details,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ERA-Bench scenarios through the refactored ERA pipeline.")
    parser.add_argument("--category", default=None, help="Optional single category to run.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios for quick runs.")
    parser.add_argument("--mode", default=None, help="Optional pipeline mode override (quick/meeting/war/darbar).")
    parser.add_argument("--scenarios-root", default="era_benchmark", help="Path to benchmark root.")
    args = parser.parse_args()

    summary = run_benchmark(
        scenarios_root=Path(args.scenarios_root),
        limit=args.limit,
        category=args.category,
        requested_mode=args.mode,
    )

    print("ERA Benchmark Results")
    print(f"scenarios tested: {summary['scenario_count']}")
    print(f"average score: {summary['average_score']:.4f}")
    print("category scores")
    for cat, score in summary["category_scores"].items():
        print(f"  {cat}: {score:.4f}")


if __name__ == "__main__":
    main()
