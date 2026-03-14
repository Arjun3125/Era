"""Run an ablation study across named experiments."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import json
from modules.evaluation_engine.runner import EvaluationRunner, load_scenarios

from experiments.experiment_config import DatasetSpec, resolve_dataset
from experiments.experiment_registry import EXPERIMENTS
from experiments.metrics_writer import write_json
from experiments.stats import effect_size, paired_t_test
from experiments.utils import seed_everything, utc_timestamp


def load_split_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {str(item) for item in payload}
    if "scenario_ids" in payload:
        return {str(item) for item in payload["scenario_ids"]}
    raise ValueError(f"Unsupported split format in {path}.")


def _run_config(
    config: Any,
    dataset_spec: DatasetSpec,
    scenarios: List[Dict[str, Any]],
    seed: int,
) -> Dict[str, Any]:
    seed_everything(seed)
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
        policy_model_path=config.policy_model_path,
        policy_weight=config.policy_weight,
        policy_top_k=config.policy_top_k,
    )
    summary = runner.run()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ablation study across experiments.")
    parser.add_argument("--experiments", required=True, help="Comma-separated experiment names.")
    parser.add_argument("--baseline", default=None, help="Experiment name to use as baseline.")
    parser.add_argument("--seed", type=int, default=42, help="Seed for deterministic runs.")
    args = parser.parse_args()

    names = [name.strip() for name in args.experiments.split(",") if name.strip()]
    if not names:
        raise SystemExit("No experiments specified.")
    for name in names:
        if name not in EXPERIMENTS:
            raise SystemExit(f"Unknown experiment: {name}")

    baseline_name = args.baseline or names[0]
    if baseline_name not in names:
        raise SystemExit("Baseline must be one of the experiment names.")

    configs = {name: EXPERIMENTS[name] for name in names}
    dataset_spec = resolve_dataset(configs[baseline_name].dataset)
    split_ids = load_split_ids(dataset_spec.split_file)
    scenarios = load_scenarios(dataset_spec.root, scenario_ids=split_ids)

    summaries: Dict[str, Dict[str, Any]] = {}
    per_scenario_correct: Dict[str, List[int]] = {}

    for name, config in configs.items():
        if config.dataset != configs[baseline_name].dataset:
            raise SystemExit("All experiments must use the same dataset for ablation.")
        summary = _run_config(config, dataset_spec, scenarios, args.seed)
        summaries[name] = summary
        per_scenario_correct[name] = [
            int(item["era"]["decision_correct"]) for item in summary.get("results", [])
        ]

    baseline_scores = per_scenario_correct[baseline_name]
    comparison: Dict[str, Any] = {}
    for name, scores in per_scenario_correct.items():
        if name == baseline_name:
            continue
        t_stat, p_value = paired_t_test(scores, baseline_scores)
        comparison[name] = {
            "t_stat": t_stat,
            "p_value": p_value,
            "effect_size": effect_size(scores, baseline_scores),
        }

    table = []
    for name, summary in summaries.items():
        era = summary.get("era", {})
        table.append(
            {
                "experiment": name,
                "accuracy": era.get("accuracy", 0.0),
                "ece": era.get("ece", 0.0),
                "avg_regret": era.get("avg_regret", 0.0),
                "rubric_score": era.get("rubric_score", 0.0),
                "brier_score": era.get("brier_score", 0.0),
            }
        )

    output_root = Path("experiments") / "results" / str(configs[baseline_name].dataset)
    report = {
        "timestamp": utc_timestamp(),
        "baseline": baseline_name,
        "dataset": configs[baseline_name].dataset,
        "comparison": comparison,
        "metrics": table,
    }
    write_json(output_root / "ablation_report.json", report)

    print("Ablation summary")
    for row in table:
        print(
            f"{row['experiment']}: accuracy={row['accuracy']:.4f} "
            f"ece={row['ece']:.4f} regret={row['avg_regret']:.4f}"
        )
    print(f"Wrote ablation report to {output_root / 'ablation_report.json'}")


if __name__ == "__main__":
    main()
