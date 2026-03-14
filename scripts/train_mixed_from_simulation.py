"""Train policy/value/council models on a mixed benchmark + simulated dataset."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.value_model import dataset_builder as value_builder
from modules.policy_model import dataset_builder as policy_builder
from modules.council_learning import dataset_builder as council_builder


def _write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True))
            handle.write("\n")


def _mix_rows(
    *,
    benchmark_rows: List[Dict[str, Any]],
    simulated_rows: List[Dict[str, Any]],
    benchmark_share: float,
    seed: int,
) -> List[Dict[str, Any]]:
    if not simulated_rows:
        return list(benchmark_rows)
    if not benchmark_rows:
        return list(simulated_rows)

    share = max(0.0, min(1.0, float(benchmark_share)))
    if share <= 0.0:
        return list(simulated_rows)
    if share >= 1.0:
        return list(benchmark_rows)

    rng = random.Random(seed)
    sim_count = len(simulated_rows)
    desired_total = int(round(sim_count / (1.0 - share)))
    desired_bench = max(1, desired_total - sim_count)

    if desired_bench <= len(benchmark_rows):
        bench_sample = rng.sample(benchmark_rows, desired_bench)
    else:
        bench_sample = [rng.choice(benchmark_rows) for _ in range(desired_bench)]

    mixed = list(simulated_rows) + bench_sample
    rng.shuffle(mixed)
    return mixed


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train models on mixed benchmark + simulated data.")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--simulated", default="data/simulated/decision_env.jsonl")
    parser.add_argument("--benchmark-share", type=float, default=0.4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--value-dataset", default="data/value_model/datasets/mixed_v1.jsonl")
    parser.add_argument("--policy-dataset", default="data/policy_model/datasets/mixed_v1.jsonl")
    parser.add_argument("--council-dataset", default="data/council_learning/datasets/mixed_v1.jsonl")
    parser.add_argument("--value-output", default="data/value_model/model_mixed_v1")
    parser.add_argument("--policy-output", default="data/policy_model/model_mixed_v1")
    parser.add_argument("--council-output", default="data/council_learning/model_mixed_v1")
    parser.add_argument("--value-model-type", default="ridge", help="mlp|ridge|random_forest")
    parser.add_argument("--policy-model-type", default="logistic", help="logistic|random_forest")
    parser.add_argument("--council-model-type", default="mlp", help="mlp|ridge")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--skip-council", action="store_true")
    args = parser.parse_args()

    simulated_path = Path(args.simulated)
    if not simulated_path.exists():
        raise FileNotFoundError(f"Simulated dataset not found: {simulated_path}")

    scenarios_root = Path(args.scenarios_root)
    benchmark_value = [row.as_dict() for row in value_builder.build_dataset(
        scenarios_root=scenarios_root,
        output_path=Path(args.value_dataset).with_suffix(".bench.jsonl"),
    )]
    benchmark_policy = [row.as_dict() for row in policy_builder.build_dataset(
        scenarios_root=scenarios_root,
        output_path=Path(args.policy_dataset).with_suffix(".bench.jsonl"),
    )]
    benchmark_council = [row.as_dict() for row in council_builder.build_dataset(
        scenarios_root=scenarios_root,
        output_path=Path(args.council_dataset).with_suffix(".bench.jsonl"),
    )]

    simulated_value = [row.as_dict() for row in value_builder.build_dataset_from_simulated(
        simulated_path=simulated_path,
        output_path=Path(args.value_dataset).with_suffix(".sim.jsonl"),
    )]
    simulated_policy = [row.as_dict() for row in policy_builder.build_dataset_from_simulated(
        simulated_path=simulated_path,
        output_path=Path(args.policy_dataset).with_suffix(".sim.jsonl"),
    )]
    simulated_council = [row.as_dict() for row in council_builder.build_dataset_from_simulated(
        simulated_path=simulated_path,
        output_path=Path(args.council_dataset).with_suffix(".sim.jsonl"),
    )]

    mixed_value = _mix_rows(
        benchmark_rows=benchmark_value,
        simulated_rows=simulated_value,
        benchmark_share=args.benchmark_share,
        seed=args.seed,
    )
    mixed_policy = _mix_rows(
        benchmark_rows=benchmark_policy,
        simulated_rows=simulated_policy,
        benchmark_share=args.benchmark_share,
        seed=args.seed,
    )
    mixed_council = _mix_rows(
        benchmark_rows=benchmark_council,
        simulated_rows=simulated_council,
        benchmark_share=args.benchmark_share,
        seed=args.seed,
    )

    _write_jsonl(Path(args.value_dataset), mixed_value)
    _write_jsonl(Path(args.policy_dataset), mixed_policy)
    _write_jsonl(Path(args.council_dataset), mixed_council)

    root = Path(__file__).resolve().parents[1]
    python = sys.executable

    run(
        [
            python,
            "-m",
            "modules.value_model.train",
            "--dataset",
            args.value_dataset,
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
