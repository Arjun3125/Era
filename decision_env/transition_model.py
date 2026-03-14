"""Transition dynamics for multi-step decision environment episodes."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Dict, Mapping
import random

from .scenario_generator import DecisionScenario
from .state_model import (
    DecisionState,
    StateTransition,
    LongHorizonState,
    clamp_cash,
    clamp_metric,
    clamp_risk,
    clamp_unit,
)
from .market_dynamics import apply_market_shock


@dataclass
class TransitionModel:
    """Deterministic transition model with optional noise."""

    step_scale: float = 0.35
    noise: float = 0.0
    seed: int | None = None

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def step(
        self,
        state: DecisionState,
        action_label: str,
        scenario: DecisionScenario,
    ) -> StateTransition:
        label = str(action_label).strip().upper()
        option_metrics = scenario.simulated_outcomes.get(label, {})
        metrics_delta: Dict[str, float] = {}
        next_metrics: Dict[str, float] = dict(state.metrics)

        for metric_name, raw_delta in option_metrics.items():
            scaled = float(raw_delta) * self.step_scale
            if self.noise > 0:
                scaled += self._rng.uniform(-self.noise, self.noise)
            metrics_delta[metric_name] = round(scaled, 4)

        for metric_name, delta in metrics_delta.items():
            previous = float(next_metrics.get(metric_name, 0.0))
            next_metrics[metric_name] = clamp_metric(metric_name, previous + float(delta))

        next_state = DecisionState(
            scenario_id=state.scenario_id,
            domain=state.domain,
            step_index=state.step_index + 1,
            metrics=next_metrics,
            context=state.context,
            metadata=dict(state.metadata),
        )
        terminated = self._check_terminal(next_metrics)
        return StateTransition(
            previous_state=state,
            next_state=next_state,
            action_label=label,
            metrics_delta=metrics_delta,
            terminated=terminated,
        )

    @staticmethod
    def _check_terminal(metrics: Mapping[str, float]) -> bool:
        if metrics.get("survival") is not None and float(metrics["survival"]) <= -50.0:
            return True
        if metrics.get("cash_runway") is not None and float(metrics["cash_runway"]) <= 0.0:
            return True
        if metrics.get("risk") is not None and float(metrics["risk"]) >= 90.0:
            return True
        return False


@dataclass
class LongHorizonTransitionModel:
    """Transition model for strategic long-horizon simulations."""

    seed: int | None = None

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def step(self, state: LongHorizonState, action_label: str) -> LongHorizonState:
        action = str(action_label).strip().lower()
        new_state = replace(state, step_index=state.step_index + 1)

        if action in {"launch_feature", "build_feature"}:
            new_state = replace(
                new_state,
                product_quality=clamp_unit(new_state.product_quality + 0.05),
                innovation=clamp_unit(new_state.innovation + 0.04),
                cash=clamp_cash(new_state.cash - 120_000.0),
                risk_level=clamp_risk(new_state.risk_level + 0.02),
            )
        elif action in {"increase_marketing", "boost_marketing"}:
            new_state = replace(
                new_state,
                market_share=clamp_unit(new_state.market_share + 0.03),
                marketing_strength=clamp_unit(new_state.marketing_strength + 0.02),
                cash=clamp_cash(new_state.cash - 80_000.0),
                risk_level=clamp_risk(new_state.risk_level + 0.01),
            )
        elif action in {"cut_price", "lower_price"}:
            new_state = replace(
                new_state,
                market_share=clamp_unit(new_state.market_share + 0.02),
                cash=clamp_cash(new_state.cash - 50_000.0),
                risk_level=clamp_risk(new_state.risk_level + 0.05),
            )
        elif action in {"focus_profit", "raise_price"}:
            new_state = replace(
                new_state,
                cash=clamp_cash(new_state.cash + 60_000.0),
                market_share=clamp_unit(new_state.market_share - 0.01),
                risk_level=clamp_risk(new_state.risk_level - 0.01),
            )

        new_state = apply_market_shock(new_state, rng=self._rng)

        # Strategic drift
        new_state = replace(
            new_state,
            reputation=clamp_unit(new_state.reputation + 0.01 * new_state.product_quality),
            innovation=clamp_unit(new_state.innovation * 0.99),
            competitor_strength=clamp_unit(new_state.competitor_strength + 0.005),
        )
        return new_state
