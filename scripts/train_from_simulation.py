"""Generate simulated data and train policy/value/council models."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train models from the decision simulation environment.")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--num-scenarios", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--simulated-output", default="data/simulated/decision_env.jsonl")
    parser.add_argument("--alignment-weight", type=float, default=0.4)
    parser.add_argument("--category-weights", default=None, help="JSON file with category->weight overrides.")
    parser.add_argument("--value-dataset", default="data/value_model/datasets/simulated_v1.jsonl")
    parser.add_argument("--policy-dataset", default="data/policy_model/datasets/simulated_v1.jsonl")
    parser.add_argument("--council-dataset", default="data/council_learning/datasets/simulated_v1.jsonl")
    parser.add_argument("--value-output", default="data/value_model/model_sim_v1")
    parser.add_argument("--policy-output", default="data/policy_model/model_sim_v1")
    parser.add_argument("--council-output", default="data/council_learning/model_sim_v1")
    parser.add_argument("--value-model-type", default="ridge", help="mlp|ridge|random_forest")
    parser.add_argument("--policy-model-type", default="logistic", help="logistic|random_forest")
    parser.add_argument("--council-model-type", default="mlp", help="mlp|ridge")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--skip-council", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    python = sys.executable

    sim_cmd = [
        python,
        str(root / "scripts" / "generate_simulated_data.py"),
        "--scenarios-root",
        args.scenarios_root,
        "--num-scenarios",
        str(args.num_scenarios),
        "--seed",
        str(args.seed),
        "--output",
        args.simulated_output,
        "--alignment-weight",
        str(args.alignment_weight),
    ]
    if args.category_weights:
        sim_cmd.extend(["--category-weights", args.category_weights])
    run(sim_cmd)

    run(
        [
            python,
            "-m",
            "modules.value_model.train",
            "--dataset",
            args.value_dataset,
            "--simulated",
            args.simulated_output,
            "--output",
            args.value_output,
            "--model-type",
            args.value_model_type,
            "--test-size",
            str(args.test_size),
            "--seed",
            str(args.seed),
        ]
    )

    run(
        [
            python,
            "-m",
            "modules.policy_model.train",
            "--dataset",
            args.policy_dataset,
            "--simulated",
            args.simulated_output,
            "--output",
            args.policy_output,
            "--model-type",
            args.policy_model_type,
            "--test-size",
            str(args.test_size),
            "--seed",
            str(args.seed),
        ]
    )

    if not args.skip_council:
        run(
            [
                python,
                "-m",
                "modules.council_learning.train",
                "--dataset",
                args.council_dataset,
                "--simulated",
                args.simulated_output,
                "--output",
                args.council_output,
                "--model-type",
                args.council_model_type,
                "--test-size",
                str(args.test_size),
                "--seed",
                str(args.seed),
            ]
        )


if __name__ == "__main__":
    main()
