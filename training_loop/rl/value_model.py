"""Lightweight linear value model for RL updates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ValueModel:
    weights: np.ndarray
    bias: float

    @classmethod
    def initialize(cls, *, feature_dim: int) -> "ValueModel":
        return cls(weights=np.zeros((feature_dim,), dtype=float), bias=0.0)

    def predict(self, features: np.ndarray) -> float:
        return float(np.dot(self.weights, features) + self.bias)

    def update(self, features: np.ndarray, target: float, lr: float) -> None:
        prediction = self.predict(features)
        error = float(target) - prediction
        self.weights += float(lr) * error * features
        self.bias += float(lr) * error

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"weights": self.weights.tolist(), "bias": float(self.bias)}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ValueModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        weights = np.asarray(payload["weights"], dtype=float)
        bias = float(payload.get("bias", 0.0))
        return cls(weights=weights, bias=bias)
