"""Router model definitions."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.ensemble import RandomForestClassifier


@dataclass
class RouterModelConfig:
    model_type: str = "logistic"
    max_iter: int = 1000
    random_state: int = 42
    rf_trees: int = 300
    rf_max_depth: int | None = None
    rf_min_samples_leaf: int = 2


def build_router_classifier(config: RouterModelConfig):
    model_type = (config.model_type or "logistic").lower()
    if model_type == "random_forest":
        base = RandomForestClassifier(
            n_estimators=config.rf_trees,
            max_depth=config.rf_max_depth,
            min_samples_leaf=config.rf_min_samples_leaf,
            class_weight="balanced",
            random_state=config.random_state,
        )
        return OneVsRestClassifier(base)
    base = LogisticRegression(
        max_iter=config.max_iter,
        class_weight="balanced",
        solver="liblinear",
        random_state=config.random_state,
    )
    return OneVsRestClassifier(base)
