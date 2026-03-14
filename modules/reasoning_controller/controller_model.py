"""Models for reasoning controller budgets."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier


@dataclass
class ControllerModelConfig:
    model_type: str = "mlp"
    hidden_layers: tuple[int, ...] = (128, 64)
    max_iter: int = 500
    random_state: int = 42


def build_controller_classifier(config: ControllerModelConfig):
    model_type = (config.model_type or "mlp").lower()
    if model_type == "logistic":
        return LogisticRegression(
            max_iter=config.max_iter,
            multi_class="auto",
            class_weight="balanced",
            random_state=config.random_state,
        )
    return MLPClassifier(
        hidden_layer_sizes=config.hidden_layers,
        max_iter=config.max_iter,
        random_state=config.random_state,
    )
