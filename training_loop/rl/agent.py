"""RL agent wrapper for policy/value models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from decision_env.state_model import DecisionState
from .features import FeatureSpec, featurize_state
from .policy_model import PolicyModel
from .value_model import ValueModel


@dataclass
class RLAgent:
    policy: PolicyModel
    value: ValueModel
    feature_spec: FeatureSpec
    rng: np.random.Generator

    def act(
        self,
        state: DecisionState,
        action_labels: List[str],
        temperature: float,
    ) -> Tuple[str, int, np.ndarray]:
        features = featurize_state(state, self.feature_spec)
        action_count = len(action_labels)
        action_index, probs = self.policy.sample_action(
            features,
            action_count=action_count,
            temperature=temperature,
            rng=self.rng,
        )
        return action_labels[action_index], action_index, probs

    def value_estimate(self, state: DecisionState) -> float:
        features = featurize_state(state, self.feature_spec)
        return self.value.predict(features)
