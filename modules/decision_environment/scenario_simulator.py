"""Scenario simulation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .outcome_model import Outcome, OutcomeModel, RuleOutcomeModel
from .reward_function import RewardFunction, RewardConfig


@dataclass
class SimulationResult:
    outcome: Outcome
    reward: float


class ScenarioSimulator:
    def __init__(
        self,
        *,
        outcome_model: OutcomeModel | None = None,
        reward_function: RewardFunction | None = None,
    ) -> None:
        self.outcome_model = outcome_model or RuleOutcomeModel()
        self.reward_function = reward_function or RewardFunction(RewardConfig())

    def simulate(self, scenario: Dict[str, Any], decision: str) -> SimulationResult:
        outcome = self.outcome_model.predict(scenario, decision)
        reward = self.reward_function.compute(outcome)
        return SimulationResult(outcome=outcome, reward=reward)
