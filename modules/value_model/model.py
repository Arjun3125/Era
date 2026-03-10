"""Value model architecture utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass
class ModelConfig:
    hidden_layers: Tuple[int, ...] = (256, 64)
    max_iter: int = 500
    random_state: int = 42


def build_regressor(config: ModelConfig) -> Pipeline:
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
