"""Generate simulated training data using the decision environment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.decision_environment import DecisionEnvironment, ScenarioSimulator
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
    parser.add_argument("--output", default="data/simulated/decision_env.jsonl")
    args = parser.parse_args()

    scenarios = load_scenarios(Path(args.scenarios_root), limit=args.limit)
    provider = build_scenario_provider(scenarios)
    env = DecisionEnvironment(provider, simulator=ScenarioSimulator())

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for scenario in scenarios:
            options = scenario.get("decision_options", [])
            for option in options:
                env.reset()
                result = env.step(str(option))
                row = {
                    "scenario_id": scenario.get("scenario_id"),
                    "category": scenario.get("category"),
                    "prompt": scenario.get("prompt"),
                    "option": str(option),
                    "context": scenario.get("context", {}),
                    "outcome": result.outcome,
                    "reward": result.reward,
                }
                handle.write(json.dumps(row, ensure_ascii=True))
                handle.write("\n")


if __name__ == "__main__":
    main()
