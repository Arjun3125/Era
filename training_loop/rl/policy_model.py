"""Lightweight softmax policy model for RL updates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np


def _softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    temp = max(1e-6, float(temperature))
    scaled = logits / temp
    scaled = scaled - np.max(scaled)
    exp = np.exp(scaled)
    return exp / np.sum(exp)


def _entropy(probs: np.ndarray) -> float:
    return float(-np.sum(probs * np.log(probs + 1e-12)))


def _entropy_grad(probs: np.ndarray) -> np.ndarray:
    logp = np.log(probs + 1e-12)
    g = -(logp + 1.0)
    return probs * g - probs * np.sum(probs * g)


@dataclass
class PolicyModel:
    weights: np.ndarray
    bias: np.ndarray
    action_labels: List[str]

    @classmethod
    def initialize(cls, *, num_actions: int, feature_dim: int, action_labels: List[str]) -> "PolicyModel":
        weights = np.zeros((num_actions, feature_dim), dtype=float)
        bias = np.zeros((num_actions,), dtype=float)
        return cls(weights=weights, bias=bias, action_labels=list(action_labels))

    def action_probs(self, features: np.ndarray, action_count: int, temperature: float = 1.0) -> np.ndarray:
        logits = np.dot(self.weights[:action_count], features) + self.bias[:action_count]
        return _softmax(logits, temperature=temperature)

    def sample_action(
        self,
        features: np.ndarray,
        action_count: int,
        temperature: float,
        rng: np.random.Generator,
    ) -> Tuple[int, np.ndarray]:
        probs = self.action_probs(features, action_count, temperature=temperature)
        idx = int(rng.choice(len(probs), p=probs))
        return idx, probs

    def update(
        self,
        features: np.ndarray,
        action_index: int,
        advantage: float,
        lr: float,
        entropy_coef: float = 0.0,
    ) -> None:
        probs = self.action_probs(features, len(self.action_labels))
        one_hot = np.zeros_like(probs)
        one_hot[action_index] = 1.0
        grad = (one_hot - probs)[:, None] * features[None, :]
        self.weights += float(lr) * float(advantage) * grad
        self.bias += float(lr) * float(advantage) * (one_hot - probs)
        if entropy_coef > 0.0:
            grad_entropy = _entropy_grad(probs)
            self.weights += float(lr) * float(entropy_coef) * np.outer(grad_entropy, features)
            self.bias += float(lr) * float(entropy_coef) * grad_entropy

    def entropy(self, features: np.ndarray, action_count: int) -> float:
        probs = self.action_probs(features, action_count)
        return _entropy(probs)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "weights": self.weights.tolist(),
            "bias": self.bias.tolist(),
            "action_labels": list(self.action_labels),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "PolicyModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        weights = np.asarray(payload["weights"], dtype=float)
        bias = np.asarray(payload["bias"], dtype=float)
        action_labels = list(payload.get("action_labels", []))
        return cls(weights=weights, bias=bias, action_labels=action_labels)
