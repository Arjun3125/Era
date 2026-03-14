"""Evaluation phase for continuous training loop."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True)
class EvaluationConfig:
    dataset: str
    experiment_name: str
    decision_policy: str
    policy_model_path: Path
    value_model_path: Path
    value_weight: float
    policy_weight: float
    policy_top_k: Optional[int]
    runs: int
    seeds: Sequence[int]
    routing_context_file: Optional[Path] = None
    routing_context: Optional[Dict[str, Any]] = None


def run_evaluation(config: EvaluationConfig) -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    python = sys.executable

    routing_context_file = config.routing_context_file
    if config.routing_context and not routing_context_file:
        routing_context_file = Path("data/training_loop/routing_context.json")
        routing_context_file.parent.mkdir(parents=True, exist_ok=True)
        routing_context_file.write_text(
            json.dumps(config.routing_context, indent=2),
            encoding="utf-8",
        )

    cmd = [
        python,
        str(root / "experiments" / "run_benchmark.py"),
        "--model",
        config.experiment_name,
        "--dataset",
        config.dataset,
        "--decision-policy",
        config.decision_policy,
        "--policy-model",
        str(config.policy_model_path),
        "--value-model",
        str(config.value_model_path),
        "--value-weight",
        str(config.value_weight),
        "--policy-weight",
        str(config.policy_weight),
        "--runs",
        str(config.runs),
        "--seeds",
        ",".join(str(seed) for seed in config.seeds),
    ]
    if config.policy_top_k:
        cmd.extend(["--policy-top-k", str(config.policy_top_k)])
    if routing_context_file:
        cmd.extend(["--routing-context-file", str(routing_context_file)])

    subprocess.run(cmd, check=True)

    metrics_path = (
        Path("experiments")
        / "results"
        / str(config.dataset)
        / config.experiment_name
        / "metrics.json"
    )
    if not metrics_path.exists():
        raise FileNotFoundError(f"Expected metrics at {metrics_path}")
    return json.loads(metrics_path.read_text(encoding="utf-8"))
