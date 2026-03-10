"""Backward-compatible wrapper for the evaluation engine CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.evaluation_engine.runner import EvaluationRunner, load_scenarios
from modules.evaluation_engine.report import generate_report


def load_split_ids(path: Path, split: str | None) -> set[str] | None:
    if not split or split.lower() == "all":
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    split_key = split.lower()
    if isinstance(payload, list):
        return {str(item) for item in payload}
    key = f"{split_key}_scenario_ids"
    if key in payload:
        return {str(item) for item in payload[key]}
    if split_key in payload:
        return {str(item) for item in payload[split_key]}
    raise ValueError(f"Split '{split_key}' not found in {path}.")


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
    parser.add_argument("--split-file", default=None, help="Path to split.json for train/test filtering.")
    parser.add_argument("--split", default="test", help="Split to run: train|test|all.")
    parser.add_argument(
        "--decision-policy",
        default="hybrid",
        help="Decision policy: era|simulator|hybrid|hybrid_value|policy_model|hybrid_policy_value.",
    )
    parser.add_argument("--value-model", default=None, help="Path to trained value model directory.")
    parser.add_argument("--value-weight", type=float, default=0.4, help="Weight for value model scoring.")
    parser.add_argument("--policy-model", default=None, help="Path to trained policy model directory.")
    parser.add_argument("--policy-weight", type=float, default=0.6, help="Weight for policy vs value scores when combining.")
    args = parser.parse_args()

    split_ids = load_split_ids(Path(args.split_file), args.split) if args.split_file else None
    scenarios = load_scenarios(
        Path(args.scenarios_root),
        category=args.category,
        limit=args.limit,
        scenario_ids=split_ids,
    )
    runner = EvaluationRunner(
        scenarios,
        requested_mode=args.mode,
        baseline_provider=args.baseline_provider,
        baseline_model=args.baseline_model,
        baseline_temperature=args.baseline_temperature,
        enable_counterfactuals=bool(args.counterfactuals),
        decision_policy=args.decision_policy,
        value_model_path=args.value_model,
        value_weight=args.value_weight,
        policy_model_path=args.policy_model,
        policy_weight=args.policy_weight,
    )
    summary = runner.run()
    print(generate_report(summary))


if __name__ == "__main__":
    main()
