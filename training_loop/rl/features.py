"""Feature extraction for RL policy/value updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import numpy as np

from decision_env.scenario_generator import SCENARIO_DOMAINS, _SCENARIO_TEMPLATES
from decision_env.state_model import DecisionState


def default_metric_names() -> List[str]:
    keys = set()
    for template in _SCENARIO_TEMPLATES:
        for metrics in template.get("simulated_outcomes", {}).values():
            for key in metrics.keys():
                keys.add(str(key))
        for key in template.get("reward_weights", {}).keys():
            keys.add(str(key))
    return sorted(keys)


@dataclass(frozen=True)
class FeatureSpec:
    metric_names: List[str]
    domain_names: List[str]
    max_steps: int


def build_feature_spec(max_steps: int) -> FeatureSpec:
    return FeatureSpec(
        metric_names=default_metric_names(),
        domain_names=list(SCENARIO_DOMAINS),
        max_steps=max(1, int(max_steps)),
    )


def featurize_state(state: DecisionState, spec: FeatureSpec) -> np.ndarray:
    metrics = state.metrics or {}
    metric_values = [float(metrics.get(name, 0.0)) / 100.0 for name in spec.metric_names]
    domain_one_hot = [1.0 if state.domain == name else 0.0 for name in spec.domain_names]
    step_ratio = float(state.step_index) / float(spec.max_steps)
    features = metric_values + domain_one_hot + [step_ratio]
    return np.asarray(features, dtype=float)


def feature_size(spec: FeatureSpec) -> int:
    return len(spec.metric_names) + len(spec.domain_names) + 1
