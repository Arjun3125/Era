"""One-step and multi-step decision environments."""

from __future__ import annotations

from typing import Any, Optional

from .reward_function import RewardBreakdown, RewardFunction
from .scenario_generator import DecisionScenario, ScenarioGenerator
from .simulator import OutcomeSimulator, SimulationOutcome
from .state_model import (
    DecisionState,
    LongHorizonState,
    build_initial_metrics,
    clamp_cash,
    clamp_risk,
    clamp_unit,
    summarize_metrics,
)
from .transition_model import TransitionModel, LongHorizonTransitionModel
from .reward_model import RewardModel, RewardSignal, delayed_reward, shaped_reward


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


class MultiStepDecisionEnvironment:
    """Multi-step environment with state transitions and rewards."""

    def __init__(
        self,
        *,
        generator: ScenarioGenerator | None = None,
        transition_model: TransitionModel | None = None,
        reward_model: RewardModel | None = None,
        default_domain: str | None = None,
        max_steps: int = 3,
    ):
        self.generator = generator or ScenarioGenerator()
        self.transition_model = transition_model or TransitionModel()
        self.reward_model = reward_model or RewardModel()
        self.default_domain = str(default_domain or "").strip().lower() or None
        self.max_steps = max(1, int(max_steps))
        self.current_scenario: DecisionScenario | None = None
        self.current_state: DecisionState | None = None
        self.last_transition: Any = None
        self.last_reward: RewardSignal | None = None

    def reset(self, *, domain: Optional[str] = None) -> DecisionState:
        selected_domain = str(domain or self.default_domain or "").strip().lower() or None
        scenario = self.generator.generate(domain=selected_domain)
        metrics = build_initial_metrics(scenario.simulated_outcomes.values())
        context = f"{scenario.context} State metrics: {summarize_metrics(metrics)}"
        state = DecisionState(
            scenario_id=scenario.scenario_id,
            domain=scenario.domain,
            step_index=0,
            metrics=metrics,
            context=context,
            metadata={"scenario_title": scenario.title},
        )
        self.current_scenario = scenario
        self.current_state = state
        self.last_transition = None
        self.last_reward = None
        return state

    def step(self, action: Any):
        if self.current_scenario is None or self.current_state is None:
            raise RuntimeError("MultiStepDecisionEnvironment.step called before reset().")
        transition = self.transition_model.step(
            self.current_state,
            action_label=str(action),
            scenario=self.current_scenario,
        )
        reward_signal = self.reward_model.compute(self.current_scenario, transition)
        self.current_state = transition.next_state
        self.last_transition = transition
        self.last_reward = reward_signal
        done = transition.terminated or transition.next_state.step_index >= self.max_steps
        return transition.next_state, reward_signal.total, done, {
            "transition": transition,
            "reward_signal": reward_signal,
        }


class LongHorizonDecisionEnvironment:
    """Long-horizon strategic environment with slow variables and shocks."""

    def __init__(
        self,
        *,
        generator: ScenarioGenerator | None = None,
        transition_model: LongHorizonTransitionModel | None = None,
        default_domain: str | None = None,
        max_steps: int = 24,
        gamma: float = 0.99,
        risk_coef: float = 0.5,
    ):
        self.generator = generator or ScenarioGenerator()
        self.transition_model = transition_model or LongHorizonTransitionModel()
        self.default_domain = str(default_domain or "").strip().lower() or None
        self.max_steps = max(1, int(max_steps))
        self.gamma = float(gamma)
        self.risk_coef = float(risk_coef)
        self.current_scenario: DecisionScenario | None = None
        self.current_state: LongHorizonState | None = None

    def reset(self, *, domain: Optional[str] = None) -> LongHorizonState:
        selected_domain = str(domain or self.default_domain or "").strip().lower() or None
        scenario = self.generator.generate(domain=selected_domain)
        # Initialize slow variables from scenario context with reasonable defaults.
        self.current_scenario = scenario
        self.current_state = LongHorizonState(
            step_index=0,
            market_share=clamp_unit(0.2),
            cash=clamp_cash(1_500_000.0),
            product_quality=clamp_unit(0.5),
            marketing_strength=clamp_unit(0.4),
            competitor_strength=clamp_unit(0.6),
            reputation=clamp_unit(0.5),
            innovation=clamp_unit(0.4),
            risk_level=clamp_risk(0.3),
        )
        return self.current_state

    def step(self, action: Any):
        if self.current_state is None:
            raise RuntimeError("LongHorizonDecisionEnvironment.step called before reset().")
        label = str(action).strip()
        prev_state = self.current_state
        next_state = self.transition_model.step(prev_state, label)
        done = next_state.step_index >= self.max_steps
        reward_signal = shaped_reward(
            prev_state,
            next_state,
            done=done,
            gamma=self.gamma,
            risk_coef=self.risk_coef,
        )
        reward = reward_signal.total
        self.current_state = next_state
        return next_state, reward, done, {
            "reward": reward,
            "reward_signal": reward_signal.as_dict(),
        }
