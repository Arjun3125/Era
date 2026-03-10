"""Experiment configuration and dataset registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


DATASETS = {
    "benchmark_v1": Path("era_benchmark"),
}


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    dataset: str
    model: str = "era"
    mode: Optional[str] = None
    decision_policy: str = "hybrid"
    baseline_provider: str = "none"
    baseline_model: Optional[str] = None
    baseline_temperature: float = 0.0
    counterfactuals: bool = False
    runs: int = 1
    seed: int = 42


def resolve_dataset(name_or_path: str) -> Path:
    if name_or_path in DATASETS:
        return DATASETS[name_or_path]
    return Path(name_or_path)
