"""Backward-compatible wrapper for the evaluation engine CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.evaluation_engine.runner import EvaluationRunner, load_scenarios
from modules.evaluation_engine.report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ERA-Bench scenarios through the evaluation engine.")
    parser.add_argument("--category", default=None, help="Optional single category to run.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios for quick runs.")
    parser.add_argument("--mode", default=None, help="Optional pipeline mode override (quick/meeting/war/darbar).")
    parser.add_argument("--scenarios-root", default="era_benchmark", help="Path to benchmark root.")
    parser.add_argument("--baseline-provider", default="none", help="Baseline provider: none|ollama.")
    parser.add_argument("--baseline-model", default=None, help="Baseline model name (provider-specific).")
    parser.add_argument("--baseline-temperature", type=float, default=0.0, help="Baseline temperature.")
    parser.add_argument("--counterfactuals", action="store_true", help="Enable counterfactual runs.")
    parser.add_argument("--decision-policy", default="era", help="Decision policy: era|simulator|hybrid.")
    args = parser.parse_args()

    scenarios = load_scenarios(Path(args.scenarios_root), category=args.category, limit=args.limit)
    runner = EvaluationRunner(
        scenarios,
        requested_mode=args.mode,
        baseline_provider=args.baseline_provider,
        baseline_model=args.baseline_model,
        baseline_temperature=args.baseline_temperature,
        enable_counterfactuals=bool(args.counterfactuals),
        decision_policy=args.decision_policy,
    )
    summary = runner.run()
    print(generate_report(summary))


if __name__ == "__main__":
    main()
