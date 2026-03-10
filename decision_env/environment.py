"""One-step decision environment wrapped around scenario generation and simulation."""

from __future__ import annotations

from typing import Any, Optional

from .reward_function import RewardBreakdown, RewardFunction
from .scenario_generator import DecisionScenario, ScenarioGenerator
from .simulator import OutcomeSimulator, SimulationOutcome


class DecisionEnvironment:
    """Gym-like one-step environment for evaluating ERA decisions."""

    def __init__(
        self,
        *,
        generator: ScenarioGenerator | None = None,
        simulator: OutcomeSimulator | None = None,
        reward_function: RewardFunction | None = None,
        default_domain: str | None = None,
    ):
        self.generator = generator or ScenarioGenerator()
        self.simulator = simulator or OutcomeSimulator()
        self.reward_function = reward_function or RewardFunction()
        self.default_domain = str(default_domain or "").strip().lower() or None
        self.current_scenario: DecisionScenario | None = None
        self.last_outcome: SimulationOutcome | None = None
        self.last_reward_breakdown: RewardBreakdown | None = None

    def reset(self, *, domain: Optional[str] = None) -> DecisionScenario:
        selected_domain = str(domain or self.default_domain or "").strip().lower() or None
        scenario = self.generator.generate(domain=selected_domain)
        self.current_scenario = scenario
        self.last_outcome = None
        self.last_reward_breakdown = None
        return scenario

    def step(self, action: Any):
        if self.current_scenario is None:
            raise RuntimeError("DecisionEnvironment.step called before reset().")
        outcome = self.simulator.simulate(self.current_scenario, action)
        reward_breakdown = self.reward_function.compute(self.current_scenario, outcome)
        self.last_outcome = outcome
        self.last_reward_breakdown = reward_breakdown
        done = True
        return outcome, reward_breakdown.total, done
