"""Value model architecture utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor


@dataclass
class ModelConfig:
    model_type: str = "mlp"
    hidden_layers: Tuple[int, ...] = (256, 64)
    max_iter: int = 500
    random_state: int = 42
    ridge_alpha: float = 1.0
    rf_trees: int = 200
    rf_max_depth: int | None = None
    rf_min_samples_leaf: int = 2


def build_regressor(config: ModelConfig) -> Pipeline:
    model_type = (config.model_type or "mlp").lower()
    if model_type == "ridge":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler(with_mean=True)),
                ("ridge", Ridge(alpha=config.ridge_alpha)),
            ]
        )
    if model_type == "random_forest":
        return Pipeline(
            steps=[
                ("rf", RandomForestRegressor(
                    n_estimators=config.rf_trees,
                    max_depth=config.rf_max_depth,
                    min_samples_leaf=config.rf_min_samples_leaf,
                    random_state=config.random_state,
                )),
            ]
        )
    return Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=True)),
            ("mlp", MLPRegressor(
                hidden_layer_sizes=config.hidden_layers,
                max_iter=config.max_iter,
                random_state=config.random_state,
            )),
        ]
    )
