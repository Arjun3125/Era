"""CLI entrypoint for running ERA-Bench with the evaluation engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.evaluation_engine import EvaluationRunner
from modules.evaluation_engine.report import generate_report
from modules.evaluation_engine.runner import load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ERA-Bench scenarios with the evaluation engine.")
    parser.add_argument("--benchmark", default="era_benchmark", help="Benchmark root directory.")
    parser.add_argument("--category", default=None, help="Optional single category to run.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios for quick runs.")
    parser.add_argument("--mode", default=None, help="Pipeline mode override.")
    parser.add_argument("--baseline-provider", default="none", help="Baseline provider: none|ollama.")
    parser.add_argument("--baseline-model", default=None, help="Baseline model name (provider-specific).")
    parser.add_argument("--baseline-temperature", type=float, default=0.0, help="Baseline temperature.")
    parser.add_argument("--counterfactuals", action="store_true", help="Enable counterfactual runs.")
    args = parser.parse_args()

    scenarios = load_scenarios(Path(args.benchmark), category=args.category, limit=args.limit)
    runner = EvaluationRunner(
        scenarios,
        requested_mode=args.mode,
        baseline_provider=args.baseline_provider,
        baseline_model=args.baseline_model,
        baseline_temperature=args.baseline_temperature,
        enable_counterfactuals=bool(args.counterfactuals),
    )
    summary = runner.run()
    print(generate_report(summary))


if __name__ == "__main__":
    main()
