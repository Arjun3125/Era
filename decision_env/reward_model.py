"""Reward model for multi-step decision environment episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .scenario_generator import DecisionScenario
from .state_model import StateTransition, LongHorizonState


@dataclass
class RewardSignal:
    """Reward signal for one transition."""

    total: float
    components: Dict[str, float] = field(default_factory=dict)
    terminal_penalty: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "components": dict(self.components),
            "terminal_penalty": self.terminal_penalty,
            "metadata": dict(self.metadata),
        }


@dataclass
class RewardModel:
    """Compute reward from state transitions using scenario weights."""

    terminal_penalty: float = -5.0

    def compute(self, scenario: DecisionScenario, transition: StateTransition) -> RewardSignal:
        weights = scenario.reward_weights or {}
        components: Dict[str, float] = {}
        total = 0.0
        for metric_name, delta in transition.metrics_delta.items():
            weight = float(weights.get(metric_name, 0.0))
            if weight == 0.0:
                continue
            contribution = weight * float(delta)
            components[metric_name] = round(contribution, 4)
            total += contribution
        penalty = self.terminal_penalty if transition.terminated else 0.0
        total = round(total + penalty, 4)
        return RewardSignal(
            total=total,
            components=components,
            terminal_penalty=penalty,
            metadata={"terminated": transition.terminated},
        )


def strategy_potential(state: LongHorizonState) -> float:
    return (
        2.0 * state.market_share
        + 1.5 * state.product_quality
        + 1.2 * state.reputation
        + 0.8 * state.innovation
        + state.cash / 1_000_000.0
    )


def terminal_reward(state: LongHorizonState) -> float:
    return (
        5.0 * state.market_share
        + state.cash / 500_000.0
        + 3.0 * state.reputation
    )


def shaped_reward(
    prev_state: LongHorizonState,
    next_state: LongHorizonState,
    *,
    done: bool,
    gamma: float = 0.99,
    risk_coef: float = 0.5,
) -> RewardSignal:
    phi_prev = strategy_potential(prev_state)
    phi_next = strategy_potential(next_state)
    shaping = gamma * phi_next - phi_prev
    risk_penalty = float(next_state.risk_level) * risk_coef
    reward = shaping - risk_penalty
    terminal_bonus = 0.0
    if done:
        terminal_bonus = terminal_reward(next_state)
        reward += terminal_bonus
    return RewardSignal(
        total=round(reward, 4),
        components={
            "potential_prev": round(phi_prev, 4),
            "potential_next": round(phi_next, 4),
            "shaping": round(shaping, 4),
            "risk_penalty": round(risk_penalty, 4),
            "terminal_bonus": round(terminal_bonus, 4),
        },
        terminal_penalty=0.0,
        metadata={"done": done},
    )


def delayed_reward(state: LongHorizonState) -> float:
    return round(terminal_reward(state), 4)
