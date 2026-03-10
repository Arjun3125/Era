"""Experiment runner for benchmark evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.evaluation_engine.calibration import calibration_bins
from modules.evaluation_engine.runner import EvaluationRunner, load_scenarios

from experiments.experiment_config import ExperimentConfig, resolve_dataset
from experiments.experiment_registry import EXPERIMENTS
from experiments.metrics_writer import write_json
from experiments.plot_results import plot_category_scores, plot_calibration_curve, plot_score_distribution
from experiments.stats import bootstrap_ci


def extract_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "accuracy": summary.get("era", {}).get("accuracy", 0.0),
        "ece": summary.get("era", {}).get("ece", 0.0),
        "rubric_score": summary.get("era", {}).get("rubric_score", 0.0),
        "avg_regret": summary.get("era", {}).get("avg_regret", 0.0),
        "category_scores": summary.get("category_scores", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark experiments.")
    parser.add_argument("--experiment", default=None, help="Named experiment from registry.")
    parser.add_argument("--model", default="era", help="Model identifier (era).")
    parser.add_argument("--dataset", default="benchmark_v1", help="Dataset name or path.")
    parser.add_argument("--mode", default=None, help="Pipeline mode override.")
    parser.add_argument("--decision-policy", default="hybrid", help="Decision policy: era|simulator|hybrid.")
    parser.add_argument("--value-model", default=None, help="Path to trained value model directory.")
    parser.add_argument("--value-weight", type=float, default=0.4, help="Weight for value model scoring.")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap CI.")
    parser.add_argument("--baseline-provider", default="none", help="Baseline provider: none|ollama.")
    parser.add_argument("--baseline-model", default=None, help="Baseline model name.")
    parser.add_argument("--baseline-temperature", type=float, default=0.0, help="Baseline temperature.")
    parser.add_argument("--counterfactuals", action="store_true", help="Enable counterfactual runs.")
    args = parser.parse_args()

    if args.experiment:
        if args.experiment not in EXPERIMENTS:
            raise SystemExit(f"Unknown experiment: {args.experiment}")
        config = EXPERIMENTS[args.experiment]
    else:
        config = ExperimentConfig(
            name=args.model,
            dataset=args.dataset,
            model=args.model,
            mode=args.mode,
            decision_policy=args.decision_policy,
            value_model_path=args.value_model,
            value_weight=args.value_weight,
            baseline_provider=args.baseline_provider,
            baseline_model=args.baseline_model,
            baseline_temperature=args.baseline_temperature,
            counterfactuals=bool(args.counterfactuals),
            runs=args.runs,
            seed=args.seed,
        )

    dataset_path = resolve_dataset(config.dataset)
    scenarios = load_scenarios(dataset_path)

    run_summaries: List[Dict[str, Any]] = []
    scenario_scores: List[float] = []
    for _ in range(config.runs):
        runner = EvaluationRunner(
            scenarios,
            requested_mode=config.mode,
            baseline_provider=config.baseline_provider,
            baseline_model=config.baseline_model,
            baseline_temperature=config.baseline_temperature,
            enable_counterfactuals=config.counterfactuals,
            decision_policy=config.decision_policy,
            value_model_path=config.value_model_path,
            value_weight=config.value_weight,
        )
        summary = runner.run()
        run_summaries.append(summary)
        scenario_scores.extend([item["era"]["score"] for item in summary.get("results", [])])

    metrics = extract_metrics(run_summaries[0]) if run_summaries else {}
    metrics.update(
        {
            "dataset": str(config.dataset),
            "model": config.model,
            "scenarios_tested": len(scenarios),
            "runs": config.runs,
            "decision_policy": config.decision_policy,
            "mode": config.mode,
        }
    )

    ci = {
        "accuracy_mean": metrics.get("accuracy", 0.0),
        "accuracy_ci_95": bootstrap_ci(scenario_scores, seed=config.seed),
    }

    output_root = Path("experiments") / "results" / str(config.dataset) / config.name
    plots_dir = output_root / "plots"

    write_json(output_root / "metrics.json", metrics)
    write_json(output_root / "confidence_intervals.json", ci)

    if run_summaries:
        bins = calibration_bins(
            [
                {
                    "confidence": item["era"]["confidence"],
                    "correct": bool(item["era"]["decision_correct"]),
                }
                for item in run_summaries[0].get("results", [])
            ]
        )
        plot_calibration_curve(
            [b.confidence_avg for b in bins],
            [b.accuracy for b in bins],
            plots_dir,
        )
        plot_category_scores(metrics.get("category_scores", {}), plots_dir)
        plot_score_distribution(scenario_scores, plots_dir)

    print(f"Wrote metrics to {output_root}")


if __name__ == "__main__":
    main()
