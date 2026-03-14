"""MoE router model definitions."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.neural_network import MLPClassifier
from sklearn.multiclass import OneVsRestClassifier


@dataclass
class RouterModelConfig:
    hidden_layer_sizes: tuple[int, ...] = (256, 128)
    activation: str = "relu"
    max_iter: int = 500
    random_state: int = 42
    alpha: float = 1e-4


def build_router_classifier(config: RouterModelConfig) -> OneVsRestClassifier:
    base = MLPClassifier(
        hidden_layer_sizes=config.hidden_layer_sizes,
        activation=config.activation,
        max_iter=config.max_iter,
        random_state=config.random_state,
        alpha=config.alpha,
    )
    return OneVsRestClassifier(base)
