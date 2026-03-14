"""Experiment runner for benchmark evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.evaluation_engine.calibration import calibration_bins
from modules.evaluation_engine.runner import EvaluationRunner, load_scenarios

from experiments.experiment_config import ExperimentConfig, DatasetSpec, resolve_dataset
from experiments.experiment_registry import EXPERIMENTS
from experiments.metrics_writer import write_json, write_jsonl
from experiments.plot_results import plot_category_scores, plot_calibration_curve, plot_score_distribution
from experiments.stats import bootstrap_ci, mean_std
from experiments.utils import get_git_commit, seed_everything, utc_timestamp
from modules.failure_analysis import analyze_traces
from modules.failure_analysis.failure_logger import build_trace, write_traces
from modules.failure_analysis.report_generator import write_report


def extract_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "accuracy": summary.get("era", {}).get("accuracy", 0.0),
        "ece": summary.get("era", {}).get("ece", 0.0),
        "rubric_score": summary.get("era", {}).get("rubric_score", 0.0),
        "avg_regret": summary.get("era", {}).get("avg_regret", 0.0),
        "brier_score": summary.get("era", {}).get("brier_score", 0.0),
        "avg_risk_score": summary.get("era", {}).get("avg_risk_score", 0.0),
        "category_scores": summary.get("category_scores", {}),
    }


def load_split_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {str(item) for item in payload}
    if "scenario_ids" in payload:
        return {str(item) for item in payload["scenario_ids"]}
    raise ValueError(f"Unsupported split format in {path}.")


def _parse_seeds(raw: str | None, *, runs: int, base_seed: int) -> List[int]:
    if raw:
        return [int(item.strip()) for item in raw.split(",") if item.strip()]
    return [base_seed + idx for idx in range(max(1, runs))]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark experiments.")
    parser.add_argument("--experiment", default=None, help="Named experiment from registry.")
    parser.add_argument("--model", default="era", help="Model identifier (era).")
    parser.add_argument("--dataset", default="benchmark_v1", help="Dataset name or path.")
    parser.add_argument("--mode", default=None, help="Pipeline mode override.")
    parser.add_argument("--decision-policy", default="hybrid", help="Decision policy: era|simulator|hybrid.")
    parser.add_argument("--value-model", default=None, help="Path to trained value model directory.")
    parser.add_argument("--value-weight", type=float, default=0.4, help="Weight for value model scoring.")
    parser.add_argument("--policy-model", default=None, help="Path to trained policy model directory.")
    parser.add_argument(
        "--policy-weight",
        type=float,
        default=0.6,
        help="Weight for policy vs value scores when combining.",
    )
    parser.add_argument("--policy-top-k", type=int, default=None, help="Restrict reasoning to top-K policy options.")
    parser.add_argument("--routing-context", default=None, help="JSON string for routing context overrides.")
    parser.add_argument("--routing-context-file", default=None, help="Path to JSON routing context overrides.")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for bootstrap CI.")
    parser.add_argument("--seeds", default=None, help="Comma-separated seeds (overrides --runs/--seed).")
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
            policy_model_path=args.policy_model,
            policy_weight=args.policy_weight,
            policy_top_k=args.policy_top_k,
            routing_context_file=args.routing_context_file,
            baseline_provider=args.baseline_provider,
            baseline_model=args.baseline_model,
            baseline_temperature=args.baseline_temperature,
            counterfactuals=bool(args.counterfactuals),
            runs=args.runs,
            seed=args.seed,
        )

    routing_context: Dict[str, Any] | None = None
    routing_context_file = config.routing_context_file or args.routing_context_file
    if routing_context_file:
        payload = json.loads(Path(routing_context_file).read_text(encoding="utf-8-sig").lstrip("\ufeff"))
        if not isinstance(payload, dict):
            raise ValueError("routing-context-file must contain a JSON object.")
        routing_context = dict(payload)
    if args.routing_context:
        payload = json.loads(args.routing_context)
        if not isinstance(payload, dict):
            raise ValueError("routing-context must be a JSON object.")
        routing_context = {**(routing_context or {}), **payload}

    dataset_spec: DatasetSpec = resolve_dataset(config.dataset)
    split_ids = load_split_ids(dataset_spec.split_file)
    scenarios = load_scenarios(dataset_spec.root, scenario_ids=split_ids)
    scenario_map = {scenario.get("scenario_id"): scenario for scenario in scenarios}

    seeds = _parse_seeds(args.seeds, runs=config.runs, base_seed=config.seed)
    run_summaries: List[Dict[str, Any]] = []
    scenario_scores: List[float] = []
    scenario_correct: List[float] = []
    scenario_rubric: List[float] = []
    scenario_regret: List[float] = []
    run_metrics: List[Dict[str, Any]] = []
    output_root = Path("experiments") / "results" / str(config.dataset) / config.name
    runs_dir = output_root / "runs"

    for seed in seeds:
        seed_everything(seed)
        runner = EvaluationRunner(
            scenarios,
            requested_mode=config.mode,
            routing_context=routing_context,
            baseline_provider=config.baseline_provider,
            baseline_model=config.baseline_model,
            baseline_temperature=config.baseline_temperature,
            enable_counterfactuals=config.counterfactuals,
            decision_policy=config.decision_policy,
            value_model_path=config.value_model_path,
            value_weight=config.value_weight,
            policy_model_path=config.policy_model_path,
            policy_weight=config.policy_weight,
            policy_top_k=config.policy_top_k,
        )
        summary = runner.run()
        run_summaries.append(summary)
        scenario_scores.extend([item["era"]["score"] for item in summary.get("results", [])])
        scenario_correct.extend([item["era"]["decision_correct"] for item in summary.get("results", [])])
        scenario_rubric.extend([item["era"]["rubric_score"] for item in summary.get("results", [])])
        scenario_regret.extend([item["era"]["regret"] for item in summary.get("results", [])])
        run_metrics.append(
            {
                **extract_metrics(summary),
                "seed": seed,
                "scenario_count": len(scenarios),
                "budget_distribution": summary.get("budget_distribution", {}),
                "avg_budget": summary.get("avg_budget", 0.0),
            }
        )

        run_dir = runs_dir / f"seed_{seed}"
        write_json(run_dir / "summary.json", summary)
        per_scenario = [
            {
                "scenario_id": item.get("scenario_id"),
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "expected_decision": item.get("expected_decision"),
                "decision": item["era"].get("decision"),
                "decision_correct": item["era"].get("decision_correct"),
                "score": item["era"].get("score"),
                "confidence": item["era"].get("confidence"),
                "confidence_calibrated": item["era"].get("confidence_calibrated"),
                "risk_score": item["era"].get("risk_score"),
                "policy_entropy": item["era"].get("policy_entropy"),
                "value_variance": item["era"].get("value_variance"),
                "reasoning_budget": item["era"].get("reasoning_budget"),
            }
            for item in summary.get("results", [])
        ]
        write_jsonl(run_dir / "results.jsonl", per_scenario)

        traces = [
            build_trace(
                scenario=scenario_map.get(item.get("scenario_id"), {}),
                result=item,
            )
            for item in summary.get("results", [])
        ]
        write_traces(run_dir / "traces.jsonl", traces)
        trace_stub = f"{str(config.dataset).replace('/', '_')}_{config.name}_seed_{seed}"
        write_traces(Path("experiments") / "traces" / f"{trace_stub}.jsonl", traces)
        analysis = analyze_traces(traces)
        write_json(run_dir / "failure_stats.json", analysis.as_dict())
        write_report(run_dir / "failure_report.md", analysis)

    metrics = extract_metrics(run_summaries[0]) if run_summaries else {}
    if run_summaries:
        category_scores: Dict[str, List[float]] = {}
        for summary in run_summaries:
            for cat, score in summary.get("category_scores", {}).items():
                category_scores.setdefault(cat, []).append(score)
        metrics["category_scores"] = {
            cat: round(sum(values) / len(values), 4) for cat, values in category_scores.items()
        }
    if run_metrics:
        for key in ("accuracy", "ece", "rubric_score", "avg_regret", "brier_score", "avg_risk_score"):
            values = [run.get(key, 0.0) for run in run_metrics]
            mean_value, std_value = mean_std(values)
            metrics[key] = mean_value
            metrics[f"{key}_std"] = std_value
    metrics.update(
        {
            "dataset": str(config.dataset),
            "dataset_version": dataset_spec.version,
            "model": config.model,
            "scenarios_tested": len(scenarios),
            "runs": len(seeds),
            "decision_policy": config.decision_policy,
            "mode": config.mode,
        }
    )

    ci = {
        "accuracy_mean": metrics.get("accuracy", 0.0),
        "accuracy_ci_95": bootstrap_ci(scenario_correct, seed=config.seed),
        "rubric_mean": metrics.get("rubric_score", 0.0),
        "rubric_ci_95": bootstrap_ci(scenario_rubric, seed=config.seed),
        "avg_regret_mean": metrics.get("avg_regret", 0.0),
        "avg_regret_ci_95": bootstrap_ci(scenario_regret, seed=config.seed),
    }

    plots_dir = output_root / "plots"

    write_json(output_root / "metrics.json", metrics)
    write_json(output_root / "confidence_intervals.json", ci)
    write_json(
        output_root / "experiment.json",
        {
            "experiment_name": config.name,
            "dataset": config.dataset,
            "dataset_version": dataset_spec.version,
            "dataset_root": str(dataset_spec.root),
            "split_file": str(dataset_spec.split_file) if dataset_spec.split_file else None,
            "timestamp": utc_timestamp(),
            "git_commit": get_git_commit(),
            "config": asdict(config),
            "seeds": seeds,
        },
    )
    write_jsonl(output_root / "runs.jsonl", run_metrics)

    if run_summaries:
        bins = calibration_bins(
            [
                {
                    "confidence": item["era"].get("confidence_calibrated", item["era"]["confidence"]),
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
