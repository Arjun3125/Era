"""Run a single experiment entry via the benchmark runner."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ExperimentResult:
    name: str
    status: str
    runtime_sec: float
    metrics: Dict[str, Any]
    stdout: str
    stderr: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "runtime_sec": round(self.runtime_sec, 3),
            "metrics": self.metrics,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def run_experiment(exp: Dict[str, Any], *, repo_root: Path) -> ExperimentResult:
    name = str(exp.get("name") or "experiment").strip()
    dataset = exp.get("dataset", "benchmark_v1_test")
    decision_policy = exp.get("decision_policy", "hybrid_all")
    policy_model = exp.get("policy_model")
    value_model = exp.get("value_model")
    routing_context_file = exp.get("routing_context_file")
    runs = exp.get("runs", 1)
    seeds = exp.get("seeds")

    cmd = [
        sys.executable,
        str(repo_root / "experiments" / "run_benchmark.py"),
        "--model",
        name,
        "--dataset",
        str(dataset),
        "--decision-policy",
        str(decision_policy),
        "--runs",
        str(runs),
    ]
    if policy_model:
        cmd.extend(["--policy-model", str(policy_model)])
    if value_model:
        cmd.extend(["--value-model", str(value_model)])
    if routing_context_file:
        cmd.extend(["--routing-context-file", str(routing_context_file)])
    if seeds:
        if isinstance(seeds, (list, tuple)):
            seeds_value = ",".join(str(seed) for seed in seeds)
        else:
            seeds_value = str(seeds)
        cmd.extend(["--seeds", seeds_value])

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    runtime = time.time() - start

    metrics_path = (
        repo_root
        / "experiments"
        / "results"
        / str(dataset)
        / name
        / "metrics.json"
    )
    metrics: Dict[str, Any] = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    status = "ok" if result.returncode == 0 else "failed"
    return ExperimentResult(
        name=name,
        status=status,
        runtime_sec=runtime,
        metrics=metrics,
        stdout=result.stdout,
        stderr=result.stderr,
    )
