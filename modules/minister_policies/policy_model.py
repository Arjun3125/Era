"""Minister policy model for stance distribution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from sklearn.neural_network import MLPClassifier


STANCE_LABELS = ("support", "neutral", "oppose")


@dataclass
class PolicyConfig:
    hidden_layers: tuple[int, ...] = (64, 32)
    max_iter: int = 300
    random_state: int = 42


class MinisterPolicyModel:
    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()
        self.model = MLPClassifier(
            hidden_layer_sizes=self.config.hidden_layers,
            max_iter=self.config.max_iter,
            random_state=self.config.random_state,
        )

    def fit(self, X: np.ndarray, y: List[str]) -> None:
        labels = self._encode_labels(y)
        self.model.fit(X, labels)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        probs = self.model.predict_proba(X)
        return probs

    @staticmethod
    def _encode_labels(labels: List[str]) -> List[int]:
        mapping = {label: idx for idx, label in enumerate(STANCE_LABELS)}
        return [mapping.get(str(label).strip().lower(), 1) for label in labels]

    @staticmethod
    def decode_proba(probs: np.ndarray) -> Dict[str, float]:
        if probs.ndim == 2:
            probs = probs[0]
        return {label: float(prob) for label, prob in zip(STANCE_LABELS, probs)}
