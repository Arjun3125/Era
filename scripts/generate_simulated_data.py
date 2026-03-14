"""Generate simulated training data using the decision environment."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.decision_environment import DecisionEnvironment, ScenarioSimulator
from modules.decision_simulator import DecisionSimulator
from modules.evaluation_engine.option_match import match_option
from modules.evaluation_engine.rubric_eval import rubric_score
from modules.evaluation_engine.runner import load_scenarios


def build_scenario_provider(scenarios: List[Dict[str, Any]]):
    index = 0

    def _provider() -> Dict[str, Any]:
        nonlocal index
        scenario = scenarios[index % len(scenarios)]
        index += 1
        return scenario

    return _provider


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate simulated decision outcomes.")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--num-scenarios", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shuffle", action="store_true")
    parser.add_argument("--alignment-weight", type=float, default=0.4)
    parser.add_argument("--category-weights", default=None, help="JSON file with category->weight overrides.")
    parser.add_argument("--output", default="data/simulated/decision_env.jsonl")
    args = parser.parse_args()

    scenarios = load_scenarios(Path(args.scenarios_root), limit=args.limit)
    if not scenarios:
        raise RuntimeError("No scenarios loaded for simulation.")
    rng = random.Random(args.seed)
    scenario_pool = list(scenarios)
    if args.num_scenarios is not None:
        scenario_pool = [rng.choice(scenarios) for _ in range(int(args.num_scenarios))]
    elif args.shuffle:
        rng.shuffle(scenario_pool)

    provider = build_scenario_provider(scenarios)
    env = DecisionEnvironment(provider, simulator=ScenarioSimulator())
    decision_simulator = DecisionSimulator()

    category_weights = {
        "strategy": 1.0,
        "risk": 1.1,
        "ethics": 1.05,
        "resource_allocation": 1.0,
        "long_term_tradeoffs": 1.05,
    }
    if args.category_weights:
        payload = json.loads(Path(args.category_weights).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            for key, value in payload.items():
                try:
                    category_weights[str(key)] = float(value)
                except Exception:
                    continue

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for index, scenario in enumerate(scenario_pool):
            options = scenario.get("decision_options", [])
            utilities = decision_simulator.compute_utilities(scenario)
            prediction_map = {item.option: item.prediction for item in utilities}
            expected = scenario.get("expected_decision", "")
            rubric = scenario.get("reasoning_rubric", [])
            evaluation = scenario.get("evaluation", {})
            w_decision = float(evaluation.get("decision_weight", 0.5))
            w_reason = float(evaluation.get("reasoning_weight", 0.5))
            total_weight = w_decision + w_reason
            if total_weight > 0 and abs(total_weight - 1.0) > 1e-6:
                w_decision /= total_weight
                w_reason /= total_weight
            category = str(scenario.get("category", "strategy")).strip().lower() or "strategy"
            category_weight = float(category_weights.get(category, 1.0))
            for option in options:
                env.reset()
                result = env.step(str(option))
                normalized_option = match_option(option, options) or str(option)
                decision_correct = 1 if normalized_option == expected else 0
                hints = decision_simulator.reasoning_hints(
                    scenario,
                    prediction_map.get(str(option)),
                )
                rubric_score_value = rubric_score(" ".join(hints), rubric)
                benchmark_score = w_decision * decision_correct + w_reason * rubric_score_value
                benchmark_reward = max(-1.0, min(1.0, round(2.0 * benchmark_score - 1.0, 4)))
                base_reward = float(result.reward)
                align_weight = max(0.0, min(1.0, float(args.alignment_weight)))
                aligned_reward = (1.0 - align_weight) * base_reward + align_weight * benchmark_reward
                aligned_reward = max(-1.0, min(1.0, round(aligned_reward * category_weight, 4)))
                row = {
                    "sample_id": f"sim_{index:06d}",
                    "scenario_instance": index,
                    "scenario_id": scenario.get("scenario_id"),
                    "category": scenario.get("category"),
                    "prompt": scenario.get("prompt"),
                    "option": str(option),
                    "context": scenario.get("context", {}),
                    "outcome": result.outcome,
                    "reward": aligned_reward,
                    "reward_base": base_reward,
                    "reward_benchmark": benchmark_reward,
                    "benchmark_score": round(benchmark_score, 4),
                    "alignment_weight": align_weight,
                }
                handle.write(json.dumps(row, ensure_ascii=True))
                handle.write("\n")


if __name__ == "__main__":
    main()
