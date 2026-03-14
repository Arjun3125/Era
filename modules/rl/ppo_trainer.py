"""Minimal PPO trainer for ERA decision environments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from decision_env.environment import LongHorizonDecisionEnvironment
from decision_env.state_model import LongHorizonState
from .advantage import compute_advantages, compute_returns
from .policy_network import PolicyNetwork
from .trajectory_buffer import TrajectoryBuffer
from .value_network import ValueNetwork


@dataclass
class PPOConfig:
    episodes: int = 1000
    max_steps: int = 24
    gamma: float = 0.99
    lam: float = 0.95
    clip: float = 0.2
    policy_lr: float = 3e-4
    value_lr: float = 1e-3
    epochs: int = 4
    entropy_coef: float = 0.01
    reward_scale: float = 1.0


class PPOTrainer:
    def __init__(
        self,
        *,
        environment: LongHorizonDecisionEnvironment,
        policy: PolicyNetwork,
        value: ValueNetwork,
        action_space: List[str],
        config: PPOConfig,
        seed: int = 42,
    ) -> None:
        self.environment = environment
        self.policy = policy
        self.value = value
        self.action_space = list(action_space)
        self.config = config
        self.rng = np.random.default_rng(seed)

    def train(self) -> List[dict]:
        metrics: List[dict] = []
        for episode in range(1, self.config.episodes + 1):
            buffer, total_reward = self._collect_episode()
            losses = self._update_from_buffer(buffer)
            metrics.append(
                {
                    "episode": episode,
                    "total_reward": round(total_reward, 4),
                    "policy_loss": losses[0],
                    "value_loss": losses[1],
                }
            )
        return metrics

    def _collect_episode(self) -> Tuple[TrajectoryBuffer, float]:
        buffer = TrajectoryBuffer()
        state = self.environment.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < self.config.max_steps:
            features = featurize_long_state(state)
            action_idx, log_prob, _probs = self.policy.sample_action(features, self.rng)
            action = self.action_space[action_idx]
            value_est = self.value.predict(features)

            next_state, reward, done, _info = self.environment.step(action)
            scaled_reward = float(reward) * self.config.reward_scale
            buffer.add(
                features,
                action_idx,
                scaled_reward,
                log_prob,
                value_est,
                done,
            )
            total_reward += scaled_reward
            steps += 1
            state = next_state

        return buffer, total_reward

    def _update_from_buffer(self, buffer: TrajectoryBuffer) -> Tuple[float, float]:
        batch = buffer.as_arrays()
        advantages = np.asarray(
            compute_advantages(
                batch["rewards"],
                batch["values"],
                batch["dones"],
                gamma=self.config.gamma,
                lam=self.config.lam,
            ),
            dtype=float,
        )
        returns = np.asarray(compute_returns(batch["values"], advantages), dtype=float)

        # Normalize advantages
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        policy_loss = 0.0
        value_loss = 0.0
        for _ in range(self.config.epochs):
            policy_loss = self.policy.update_ppo(
                batch["states"],
                batch["actions"],
                batch["log_probs"],
                advantages,
                clip=self.config.clip,
                lr=self.config.policy_lr,
                entropy_coef=self.config.entropy_coef,
            )
            value_loss = self.value.update(
                batch["states"],
                returns,
                lr=self.config.value_lr,
            )
        return float(policy_loss), float(value_loss)


def featurize_long_state(state: LongHorizonState) -> np.ndarray:
    return np.asarray(
        [
            state.market_share,
            state.cash / 1_000_000.0,
            state.product_quality,
            state.marketing_strength,
            state.competitor_strength,
            state.reputation,
            state.innovation,
            state.risk_level,
            state.step_index / 36.0,
        ],
        dtype=float,
    )
