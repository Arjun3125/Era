"""Outcome simulation for one-step decision environment episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from .scenario_generator import DecisionScenario


@dataclass
class SimulationOutcome:
    """Outcome produced after the agent chooses one scenario option."""

    scenario_id: str
    domain: str
    action_label: str
    action_title: str
    metrics: Dict[str, float]
    narrative: str
    terminated: bool = True
    source: str = "decision_env_simulator"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "domain": self.domain,
            "action_label": self.action_label,
            "action_title": self.action_title,
            "metrics": dict(self.metrics),
            "narrative": self.narrative,
            "terminated": self.terminated,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


class OutcomeSimulator:
    """Maps a chosen option to a deterministic simulated outcome."""

    _PENALTY_METRICS = {
        "risk",
        "regulatory_risk",
        "reputational_risk",
        "casualties",
        "burn",
    }

    def simulate(
        self,
        scenario: DecisionScenario,
        action: Any,
    ) -> SimulationOutcome:
        label = self._resolve_action_label(action)
        option = self._resolve_option(scenario, label)
        metrics = dict(scenario.simulated_outcomes.get(label, {}))
        if not metrics:
            metrics = {
                "risk": 30.0,
                "survival": -10.0,
                "optionality": -5.0,
            }
        narrative = self._build_narrative(scenario.domain, option.title, metrics)
        return SimulationOutcome(
            scenario_id=scenario.scenario_id,
            domain=scenario.domain,
            action_label=option.label,
            action_title=option.title,
            metrics=metrics,
            narrative=narrative,
            metadata={
                "selected_option": option.as_dict(),
                "available_actions": [item.as_dict() for item in scenario.options],
            },
        )

    @staticmethod
    def _resolve_action_label(action: Any) -> str:
        if isinstance(action, str):
            return action.strip().upper()
        if isinstance(action, Mapping):
            label = action.get("label") or action.get("action_label") or action.get("option")
            return str(label or "").strip().upper()
        label = getattr(action, "action_label", None) or getattr(action, "label", None)
        return str(label or "").strip().upper()

    @staticmethod
    def _resolve_option(
        scenario: DecisionScenario,
        label: str,
    ):
        for option in scenario.options:
            if option.label == label:
                return option
        return scenario.options[0]

    @staticmethod
    def _build_narrative(
        domain: str,
        action_title: str,
        metrics: Mapping[str, float],
    ) -> str:
        strongest_metric = ""
        strongest_value = float("-inf")
        weakest_metric = ""
        weakest_value = float("inf")
        for metric_name, value in metrics.items():
            numeric = float(value)
            if numeric > strongest_value:
                strongest_metric = metric_name
                strongest_value = numeric
            if numeric < weakest_value:
                weakest_metric = metric_name
                weakest_value = numeric
        strongest_verb = (
            "reduced"
            if strongest_metric in OutcomeSimulator._PENALTY_METRICS and strongest_value < 0.0
            else "increased"
            if strongest_metric in OutcomeSimulator._PENALTY_METRICS
            else "improved"
        )
        return (
            f"In {domain}, choosing '{action_title}' {strongest_verb} {strongest_metric} "
            f"most strongly ({strongest_value:+.2f}) while the hardest tradeoff appeared in "
            f"{weakest_metric} ({weakest_value:+.2f})."
        )
