"""Minimal linear value network for PPO."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ValueNetwork:
    weights: np.ndarray
    bias: float

    @classmethod
    def initialize(cls, *, feature_dim: int) -> "ValueNetwork":
        return cls(weights=np.zeros((feature_dim,), dtype=float), bias=0.0)

    def predict(self, features: np.ndarray) -> float:
        return float(np.dot(self.weights, features) + self.bias)

    def update(
        self,
        states: np.ndarray,
        returns: np.ndarray,
        *,
        lr: float,
    ) -> float:
        preds = states @ self.weights + self.bias
        errors = returns - preds
        grad_w = -2.0 * (states.T @ errors) / max(1, len(states))
        grad_b = -2.0 * float(np.mean(errors))
        self.weights -= lr * grad_w
        self.bias -= lr * grad_b
        mse = float(np.mean(errors**2))
        return mse

    def save(self, path: Path) -> None:
        payload = {"weights": self.weights.tolist(), "bias": float(self.bias)}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ValueNetwork":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            weights=np.asarray(payload["weights"], dtype=float),
            bias=float(payload.get("bias", 0.0)),
        )
