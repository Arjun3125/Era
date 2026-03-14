"""Dataset builder wrapper for MoE router training."""

from __future__ import annotations

from pathlib import Path

from modules.expert_router.dataset_builder import build_dataset


def build_moe_dataset(*, scenarios_root: Path, output_path: Path, label_threshold: float) -> None:
    build_dataset(
        scenarios_root=scenarios_root,
        output_path=output_path,
        label_threshold=label_threshold,
    )
