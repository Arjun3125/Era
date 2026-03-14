"""Minimal linear softmax policy network for PPO."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


@dataclass
class PolicyNetwork:
    weights: np.ndarray
    bias: np.ndarray
    action_labels: List[str]

    @classmethod
    def initialize(cls, *, num_actions: int, feature_dim: int, action_labels: List[str]) -> "PolicyNetwork":
        weights = np.zeros((num_actions, feature_dim), dtype=float)
        bias = np.zeros((num_actions,), dtype=float)
        return cls(weights=weights, bias=bias, action_labels=list(action_labels))

    def logits(self, features: np.ndarray) -> np.ndarray:
        return np.dot(self.weights, features) + self.bias

    def action_probs(self, features: np.ndarray) -> np.ndarray:
        return _softmax(self.logits(features))

    def sample_action(
        self,
        features: np.ndarray,
        rng: np.random.Generator,
    ) -> Tuple[int, float, np.ndarray]:
        probs = self.action_probs(features)
        action = int(rng.choice(len(probs), p=probs))
        log_prob = float(np.log(probs[action] + 1e-12))
        return action, log_prob, probs

    def log_prob(self, features: np.ndarray, action: int) -> float:
        probs = self.action_probs(features)
        return float(np.log(probs[int(action)] + 1e-12))

    def update_ppo(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        old_log_probs: np.ndarray,
        advantages: np.ndarray,
        *,
        clip: float,
        lr: float,
        entropy_coef: float = 0.0,
    ) -> float:
        grad_w = np.zeros_like(self.weights)
        grad_b = np.zeros_like(self.bias)
        loss = 0.0

        for features, action, old_logp, adv in zip(states, actions, old_log_probs, advantages):
            probs = self.action_probs(features)
            logp = float(np.log(probs[int(action)] + 1e-12))
            ratio = float(np.exp(logp - old_logp))

            use_unclipped = (
                (adv >= 0.0 and ratio <= 1.0 + clip)
                or (adv < 0.0 and ratio >= 1.0 - clip)
            )
            weight = ratio if use_unclipped else (1.0 + clip if adv >= 0.0 else 1.0 - clip)

            loss += -min(ratio * adv, weight * adv)

            if use_unclipped:
                grad_logp = np.zeros_like(probs)
                grad_logp[int(action)] = 1.0
                grad_logp -= probs
                grad_w += -adv * ratio * np.outer(grad_logp, features)
                grad_b += -adv * ratio * grad_logp

            if entropy_coef > 0.0:
                grad_entropy = _entropy_grad(probs)
                grad_w += entropy_coef * np.outer(grad_entropy, features)
                grad_b += entropy_coef * grad_entropy

        batch = max(1, len(states))
        self.weights += (lr / batch) * grad_w
        self.bias += (lr / batch) * grad_b
        return float(loss / batch)

    def save(self, path: Path) -> None:
        payload = {
            "weights": self.weights.tolist(),
            "bias": self.bias.tolist(),
            "action_labels": list(self.action_labels),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "PolicyNetwork":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            weights=np.asarray(payload["weights"], dtype=float),
            bias=np.asarray(payload["bias"], dtype=float),
            action_labels=list(payload.get("action_labels", [])),
        )


def _entropy_grad(probs: np.ndarray) -> np.ndarray:
    logp = np.log(probs + 1e-12)
    g = -(logp + 1.0)
    # (diag(p) - p p^T) * g
    return probs * g - probs * np.sum(probs * g)
