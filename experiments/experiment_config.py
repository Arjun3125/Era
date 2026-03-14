"""Experiment configuration and dataset registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class DatasetSpec:
    root: Path
    split_file: Optional[Path] = None
    version: Optional[str] = None
    description: Optional[str] = None


DATASETS: Dict[str, DatasetSpec] = {
    "benchmark_v1": DatasetSpec(
        root=Path("era_benchmark"),
        split_file=None,
        version="1.2",
        description="ERA-Bench v1.2 full dataset",
    ),
    "benchmark_v1_train": DatasetSpec(
        root=Path("era_benchmark"),
        split_file=Path("era_benchmark/splits/v1_2/train.json"),
        version="1.2",
        description="ERA-Bench v1.2 train split",
    ),
    "benchmark_v1_test": DatasetSpec(
        root=Path("era_benchmark"),
        split_file=Path("era_benchmark/splits/v1_2/test.json"),
        version="1.2",
        description="ERA-Bench v1.2 test split",
    ),
    "benchmark_v1_hard": DatasetSpec(
        root=Path("era_benchmark"),
        split_file=Path("era_benchmark/splits/v1_2/hard.json"),
        version="1.2",
        description="ERA-Bench v1.2 hard-only subset",
    ),
}


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    dataset: str
    model: str = "era"
    mode: Optional[str] = None
    decision_policy: str = "hybrid"
    value_model_path: Optional[str] = None
    value_weight: float = 0.4
    policy_model_path: Optional[str] = None
    policy_weight: float = 0.6
    policy_top_k: Optional[int] = None
    routing_context_file: Optional[str] = None
    baseline_provider: str = "none"
    baseline_model: Optional[str] = None
    baseline_temperature: float = 0.0
    counterfactuals: bool = False
    runs: int = 1
    seed: int = 42


def resolve_dataset(name_or_path: str) -> DatasetSpec:
    if name_or_path in DATASETS:
        return DATASETS[name_or_path]
    return DatasetSpec(root=Path(name_or_path))
