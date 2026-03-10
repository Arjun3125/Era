"""Experiment registry for named runs."""

from __future__ import annotations

from .experiment_config import ExperimentConfig


EXPERIMENTS = {
    "era_baseline": ExperimentConfig(name="era_baseline", dataset="benchmark_v1", model="era", mode="meeting"),
    "era_no_council": ExperimentConfig(name="era_no_council", dataset="benchmark_v1", model="era", mode="quick"),
    "era_darbar": ExperimentConfig(name="era_darbar", dataset="benchmark_v1", model="era", mode="darbar"),
}
