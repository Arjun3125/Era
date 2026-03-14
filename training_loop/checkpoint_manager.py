"""Checkpoint manager for training loop model promotion."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .training_step import ModelArtifacts


@dataclass
class CheckpointManager:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def best_metrics_path(self) -> Path:
        return self.root / "best_metrics.json"

    @property
    def best_models_path(self) -> Path:
        return self.root / "best_models.json"

    def load_best_metrics(self) -> Optional[Dict[str, Any]]:
        if not self.best_metrics_path.exists():
            return None
        return json.loads(self.best_metrics_path.read_text(encoding="utf-8"))

    def should_promote(self, new_metrics: Dict[str, Any], min_improvement: float) -> bool:
        previous = self.load_best_metrics()
        if previous is None:
            return True
        new_acc = float(new_metrics.get("accuracy", 0.0))
        old_acc = float(previous.get("accuracy", 0.0))
        return new_acc >= old_acc + float(min_improvement)

    def promote(self, artifacts: ModelArtifacts, metrics: Dict[str, Any], iteration: int) -> None:
        best_root = self.root / "best_models"
        policy_dest = best_root / "policy_model"
        value_dest = best_root / "value_model"
        council_dest = best_root / "council_model"

        self._copy_dir(artifacts.policy_model_path, policy_dest)
        self._copy_dir(artifacts.value_model_path, value_dest)
        if artifacts.council_model_path:
            self._copy_dir(artifacts.council_model_path, council_dest)

        metadata = {
            "iteration": iteration,
            "policy_model": str(policy_dest),
            "value_model": str(value_dest),
            "council_model": str(council_dest) if artifacts.council_model_path else None,
        }
        self.best_models_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        self.best_metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    @staticmethod
    def _copy_dir(source: Path, dest: Path) -> None:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
