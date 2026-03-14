"""Trajectory buffer for PPO training."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class TrajectoryBuffer:
    states: List[np.ndarray] = field(default_factory=list)
    actions: List[int] = field(default_factory=list)
    rewards: List[float] = field(default_factory=list)
    log_probs: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    dones: List[bool] = field(default_factory=list)

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        log_prob: float,
        value: float,
        done: bool,
    ) -> None:
        self.states.append(state)
        self.actions.append(int(action))
        self.rewards.append(float(reward))
        self.log_probs.append(float(log_prob))
        self.values.append(float(value))
        self.dones.append(bool(done))

    def clear(self) -> None:
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.log_probs.clear()
        self.values.clear()
        self.dones.clear()

    def as_arrays(self) -> dict:
        return {
            "states": np.asarray(self.states, dtype=float),
            "actions": np.asarray(self.actions, dtype=int),
            "rewards": np.asarray(self.rewards, dtype=float),
            "log_probs": np.asarray(self.log_probs, dtype=float),
            "values": np.asarray(self.values, dtype=float),
            "dones": np.asarray(self.dones, dtype=bool),
        }
