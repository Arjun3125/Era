from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments import experiment_config
from experiments import experiment_runner
from experiments import scheduler


def test_resolve_dataset_registry() -> None:
    spec = experiment_config.resolve_dataset("benchmark_v1_test")
    assert spec.root.name == "era_benchmark"
    assert spec.split_file is not None

    custom = experiment_config.resolve_dataset("custom/path")
    assert custom.root == Path("custom/path")


def test_scheduler_load_config_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"experiments": [{"name": "exp1"}]}), encoding="utf-8")
    config = scheduler.load_config(path)
    assert config["experiments"][0]["name"] == "exp1"


def test_scheduler_load_config_yaml(tmp_path: Path) -> None:
    yaml = pytest.importorskip("yaml")
    path = tmp_path / "config.yaml"
    path.write_text("experiments:\n  - name: exp2\n", encoding="utf-8")
    config = scheduler.load_config(path)
    assert config["experiments"][0]["name"] == "exp2"
    assert yaml is not None


def test_scheduler_run_all_monkeypatched(tmp_path: Path, monkeypatch) -> None:
    def _fake_run(exp, *, repo_root):
        class _Result:
            def as_dict(self):
                return {"name": exp.get("name", "x"), "status": "ok"}

        return _Result()

    monkeypatch.setattr(scheduler, "run_experiment", _fake_run)
    results = scheduler.run_all({"experiments": [{"name": "exp1"}]}, repo_root=tmp_path, max_workers=1)
    assert results == [{"name": "exp1", "status": "ok"}]


def test_experiment_runner_reads_metrics(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    dataset = "benchmark_v1_test"
    name = "exp1"
    metrics_path = repo_root / "experiments" / "results" / dataset / name / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps({"accuracy": 0.5}), encoding="utf-8")

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def _fake_run(cmd, capture_output, text):
        return _Proc()

    monkeypatch.setattr(experiment_runner.subprocess, "run", _fake_run)
    result = experiment_runner.run_experiment(
        {
            "name": name,
            "dataset": dataset,
            "decision_policy": "hybrid_all",
            "runs": 1,
        },
        repo_root=repo_root,
    )
    assert result.status == "ok"
    assert result.metrics["accuracy"] == 0.5
