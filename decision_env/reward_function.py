"""Reward shaping for the embedded decision environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .scenario_generator import DecisionScenario
from .simulator import SimulationOutcome


@dataclass
class RewardBreakdown:
    """Detailed reward calculation for one simulated outcome."""

    total: float
    weighted_metrics: Dict[str, float] = field(default_factory=dict)
    raw_metrics: Dict[str, float] = field(default_factory=dict)
    source: str = "decision_env_reward"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "weighted_metrics": dict(self.weighted_metrics),
            "raw_metrics": dict(self.raw_metrics),
            "source": self.source,
        }


class RewardFunction:
    """Computes scalar reward from domain-weighted simulated outcome metrics."""

    _DEFAULT_WEIGHTS = {
        "profit": 0.4,
        "market_share": 0.25,
        "brand": 0.15,
        "survival": 0.4,
        "optionality": 0.2,
        "readiness": 0.35,
        "deterrence": 0.35,
        "growth": 0.25,
        "stability": 0.3,
        "trust": 0.2,
        "strategic_position": 0.35,
        "resilience": 0.4,
        "compliance": 0.35,
        "inflation_control": 0.35,
        "risk": -0.4,
        "regulatory_risk": -0.4,
        "reputational_risk": -0.3,
        "casualties": -0.5,
        "burn": -0.2,
    }

    def compute(
        self,
        scenario: DecisionScenario,
        outcome: SimulationOutcome,
    ) -> RewardBreakdown:
        weights = dict(self._DEFAULT_WEIGHTS)
        weights.update({str(key): float(value) for key, value in scenario.reward_weights.items()})

        weighted_metrics: Dict[str, float] = {}
        total = 0.0
        for metric_name, raw_value in outcome.metrics.items():
            weight = float(weights.get(metric_name, 0.0))
            contribution = round(weight * float(raw_value), 4)
            weighted_metrics[metric_name] = contribution
            total += contribution

        return RewardBreakdown(
            total=round(total, 4),
            weighted_metrics=weighted_metrics,
            raw_metrics={key: float(value) for key, value in outcome.metrics.items()},
        )
