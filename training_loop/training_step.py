"""Training phase for continuous training loop."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ModelArtifacts:
    policy_model_path: Path
    value_model_path: Path
    council_model_path: Optional[Path]


@dataclass(frozen=True)
class TrainingConfig:
    train_mode: str
    simulated_path: Path
    scenarios_root: Path
    output_root: Path
    policy_model_type: str
    value_model_type: str
    council_model_type: str
    backend: str
    model_name: str
    st_local_only: bool
    test_size: float
    seed: int
    benchmark_share: float
    skip_council: bool


def train_models(config: TrainingConfig) -> ModelArtifacts:
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    datasets_root = output_root / "datasets"
    datasets_root.mkdir(parents=True, exist_ok=True)

    policy_output = output_root / "policy_model"
    value_output = output_root / "value_model"
    council_output = output_root / "council_model"

    python = sys.executable
    root = Path(__file__).resolve().parents[1]

    if config.train_mode == "mixed":
        subprocess.run(
            [
                python,
                str(root / "scripts" / "train_mixed_from_simulation.py"),
                "--scenarios-root",
                str(config.scenarios_root),
                "--simulated",
                str(config.simulated_path),
                "--benchmark-share",
                str(config.benchmark_share),
                "--seed",
                str(config.seed),
                "--value-dataset",
                str(datasets_root / "value_mixed.jsonl"),
                "--policy-dataset",
                str(datasets_root / "policy_mixed.jsonl"),
                "--council-dataset",
                str(datasets_root / "council_mixed.jsonl"),
                "--value-output",
                str(value_output),
                "--policy-output",
                str(policy_output),
                "--council-output",
                str(council_output),
                "--value-model-type",
                config.value_model_type,
                "--policy-model-type",
                config.policy_model_type,
                "--council-model-type",
                config.council_model_type,
                "--test-size",
                str(config.test_size),
            ]
            + (["--skip-council"] if config.skip_council else []),
            check=True,
        )
    else:
        subprocess.run(
            [
                python,
                "-m",
                "modules.value_model.train",
                "--dataset",
                str(datasets_root / "value_simulated.jsonl"),
                "--simulated",
                str(config.simulated_path),
                "--output",
                str(value_output),
                "--backend",
                config.backend,
                "--model-name",
                config.model_name,
                "--test-size",
                str(config.test_size),
                "--seed",
                str(config.seed),
                "--model-type",
                config.value_model_type,
            ]
            + (["--st-local-only"] if config.st_local_only else []),
            check=True,
        )

        subprocess.run(
            [
                python,
                "-m",
                "modules.policy_model.train",
                "--dataset",
                str(datasets_root / "policy_simulated.jsonl"),
                "--simulated",
                str(config.simulated_path),
                "--output",
                str(policy_output),
                "--backend",
                config.backend,
                "--model-name",
                config.model_name,
                "--test-size",
                str(config.test_size),
                "--seed",
                str(config.seed),
                "--model-type",
                config.policy_model_type,
            ]
            + (["--st-local-only"] if config.st_local_only else []),
            check=True,
        )

        if not config.skip_council:
            subprocess.run(
                [
                    python,
                    "-m",
                    "modules.council_learning.train",
                    "--dataset",
                    str(datasets_root / "council_simulated.jsonl"),
                    "--simulated",
                    str(config.simulated_path),
                    "--output",
                    str(council_output),
                    "--backend",
                    config.backend,
                    "--model-name",
                    config.model_name,
                    "--test-size",
                    str(config.test_size),
                    "--seed",
                    str(config.seed),
                    "--model-type",
                    config.council_model_type,
                ]
                + (["--st-local-only"] if config.st_local_only else []),
                check=True,
            )

    return ModelArtifacts(
        policy_model_path=policy_output,
        value_model_path=value_output,
        council_model_path=None if config.skip_council else council_output,
    )
