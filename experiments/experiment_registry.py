"""Experiment registry for named runs."""

from __future__ import annotations

from .experiment_config import ExperimentConfig


EXPERIMENTS = {
    "era_baseline": ExperimentConfig(name="era_baseline", dataset="benchmark_v1", model="era", mode="meeting"),
    "era_no_council": ExperimentConfig(name="era_no_council", dataset="benchmark_v1", model="era", mode="quick"),
    "era_darbar": ExperimentConfig(name="era_darbar", dataset="benchmark_v1", model="era", mode="darbar"),
    "era_value_model": ExperimentConfig(
        name="era_value_model",
        dataset="benchmark_v1",
        model="era",
        mode="meeting",
        decision_policy="value_model",
        value_model_path="data/value_model/model",
        value_weight=0.4,
    ),
}
