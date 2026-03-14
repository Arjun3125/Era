"""Generate council training data from actual minister outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.decision_pipeline import DecisionPipelineEngine
from modules.evaluation_engine.option_match import match_option
from modules.evaluation_engine.rubric_eval import rubric_score
from modules.evaluation_engine.runner import load_scenarios


def _score_decision(decision: str, reasoning: str, scenario: Dict[str, Any]) -> float:
    expected = scenario.get("expected_decision", "")
    decision_correct = 1.0 if decision == expected else 0.0
    rubric = scenario.get("reasoning_rubric", [])
    evaluation = scenario.get("evaluation", {})
    w_decision = float(evaluation.get("decision_weight", 0.5))
    w_reason = float(evaluation.get("reasoning_weight", 0.5))
    total = w_decision + w_reason
    if total > 0 and abs(total - 1.0) > 1e-6:
        w_decision /= total
        w_reason /= total
    reasoning_score = rubric_score(reasoning, rubric)
    return round(w_decision * decision_correct + w_reason * reasoning_score, 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate council learning runs from the benchmark.")
    parser.add_argument("--benchmark", default="era_benchmark")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", default="meeting")
    parser.add_argument("--output", default="data/council_learning/runs_v2.jsonl")
    parser.add_argument("--routing-context", default=None, help="JSON routing context.")
    args = parser.parse_args()

    routing_context = None
    if args.routing_context:
        payload = json.loads(args.routing_context)
        if isinstance(payload, dict):
            routing_context = payload

    scenarios = load_scenarios(Path(args.benchmark), limit=args.limit)
    engine = DecisionPipelineEngine.create()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for scenario in scenarios:
            options = scenario.get("decision_options") or []
            for option in options:
                prompt = "\n".join(
                    [
                        "Scenario:",
                        scenario.get("prompt", ""),
                        "",
                        "Options:",
                        "\n".join(f"{chr(ord('A') + idx)}. {opt}" for idx, opt in enumerate(options)),
                        "",
                        "Evaluate the following option:",
                        f"Option: {option}",
                        "Explain pros and cons.",
                        "Return score from 0-1.",
                    ]
                )
                result = engine.run(
                    user_input=prompt,
                    requested_mode=args.mode,
                    routing_context=routing_context,
                    metadata={
                        "scenario_id": scenario.get("scenario_id"),
                        "candidate_option": option,
                        "benchmark": "era_bench",
                    },
                    source="council_training",
                )
                council = result.council_result or {}
                minister_outputs = council.get("minister_outputs", {})
                decision = str(result.decision_contract.decision or "").strip().lower()
                normalized_decision = match_option(decision, options) or decision
                reasoning = str(result.decision_contract.rationale or "").strip().lower()
                score = _score_decision(normalized_decision, reasoning, scenario)
                row = {
                    "scenario_id": scenario.get("scenario_id", ""),
                    "prompt": scenario.get("prompt", ""),
                    "context": scenario.get("context", {}),
                    "option": str(option),
                    "decision": normalized_decision,
                    "score": score,
                    "minister_outputs": minister_outputs,
                }
                handle.write(json.dumps(row, ensure_ascii=True))
                handle.write("\n")


if __name__ == "__main__":
    main()
