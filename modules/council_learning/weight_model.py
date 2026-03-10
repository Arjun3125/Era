"""Weight model architecture for minister weighting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from sklearn.neural_network import MLPRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.linear_model import Ridge


@dataclass
class ModelConfig:
    model_type: str = "mlp"
    hidden_layers: Tuple[int, ...] = (128, 64)
    max_iter: int = 500
    random_state: int = 42
    ridge_alpha: float = 1.0


def build_regressor(config: ModelConfig):
    model_type = (config.model_type or "mlp").lower()
    if model_type == "ridge":
        return MultiOutputRegressor(Ridge(alpha=config.ridge_alpha))
    return MLPRegressor(
        hidden_layer_sizes=config.hidden_layers,
        max_iter=config.max_iter,
        random_state=config.random_state,
    )
