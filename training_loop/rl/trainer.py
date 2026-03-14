"""On-policy RL trainer for the decision environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from decision_env import MultiStepDecisionEnvironment
from decision_env.state_model import DecisionState
from .agent import RLAgent
from .features import FeatureSpec, featurize_state
from .policy_model import PolicyModel
from .value_model import ValueModel


@dataclass
class RLConfig:
    episodes: int
    gamma: float
    lr_policy: float
    lr_value: float
    temperature: float
    max_steps: int
    entropy_coef: float = 0.01


@dataclass
class EpisodeMetrics:
    episode_index: int
    total_reward: float
    steps: int
    avg_entropy: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "episode_index": self.episode_index,
            "total_reward": self.total_reward,
            "steps": self.steps,
            "avg_entropy": self.avg_entropy,
        }


class RLTrainer:
    def __init__(
        self,
        *,
        environment: MultiStepDecisionEnvironment,
        agent: RLAgent,
        config: RLConfig,
    ) -> None:
        self.environment = environment
        self.agent = agent
        self.config = config

    def train(self) -> List[EpisodeMetrics]:
        metrics: List[EpisodeMetrics] = []
        for episode in range(1, self.config.episodes + 1):
            episode_metrics = self._run_episode(episode)
            metrics.append(episode_metrics)
        return metrics

    def _run_episode(self, episode_index: int) -> EpisodeMetrics:
        state = self.environment.reset()
        scenario = self.environment.current_scenario
        if scenario is None:
            raise RuntimeError("Scenario missing after environment reset.")
        action_labels = [option.label for option in scenario.options]

        trajectory: List[Dict[str, np.ndarray]] = []
        total_reward = 0.0
        total_entropy = 0.0
        done = False
        steps = 0

        while not done and steps < self.config.max_steps:
            action_label, action_idx, probs = self.agent.act(
                state,
                action_labels=action_labels,
                temperature=self.config.temperature,
            )
            entropy = float(-np.sum(probs * np.log(probs + 1e-12)))
            next_state, reward, done, _info = self.environment.step(action_label)
            features = featurize_state(state, self.agent.feature_spec)
            trajectory.append(
                {
                    "features": features,
                    "action_idx": action_idx,
                    "reward": float(reward),
                }
            )
            total_reward += float(reward)
            total_entropy += entropy
            steps += 1
            state = next_state

        self._update_models(trajectory)
        return EpisodeMetrics(
            episode_index=episode_index,
            total_reward=round(total_reward, 4),
            steps=steps,
            avg_entropy=round(total_entropy / max(1, steps), 4),
        )

    def _update_models(self, trajectory: List[Dict[str, np.ndarray]]) -> None:
        returns: List[float] = []
        G = 0.0
        for step in reversed(trajectory):
            G = float(step["reward"]) + self.config.gamma * G
            returns.insert(0, G)

        for step, target in zip(trajectory, returns):
            features = step["features"]
            action_idx = int(step["action_idx"])
            value_pred = self.agent.value.predict(features)
            advantage = float(target) - value_pred
            self.agent.value.update(features, target, lr=self.config.lr_value)
            self.agent.policy.update(
                features,
                action_idx,
                advantage,
                lr=self.config.lr_policy,
                entropy_coef=self.config.entropy_coef,
            )


def initialize_agent(
    *,
    feature_spec: FeatureSpec,
    action_labels: List[str],
    seed: int,
) -> RLAgent:
    rng = np.random.default_rng(seed)
    policy = PolicyModel.initialize(
        num_actions=len(action_labels),
        feature_dim=len(featurize_state(DecisionState("", "", 0, {}, ""), feature_spec)),
        action_labels=action_labels,
    )
    value = ValueModel.initialize(feature_dim=len(featurize_state(DecisionState("", "", 0, {}, ""), feature_spec)))
    return RLAgent(policy=policy, value=value, feature_spec=feature_spec, rng=rng)
