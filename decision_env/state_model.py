"""State representation for multi-step decision environment episodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping


_PENALTY_METRICS = {
    "risk",
    "regulatory_risk",
    "reputational_risk",
    "casualties",
    "burn",
}


def clamp_metric(metric_name: str, value: float) -> float:
    metric = str(metric_name).strip().lower()
    if metric in _PENALTY_METRICS:
        return max(0.0, min(100.0, value))
    return max(-100.0, min(100.0, value))


def summarize_metrics(metrics: Mapping[str, float]) -> str:
    parts = []
    for key in sorted(metrics.keys()):
        parts.append(f"{key}={metrics[key]:+.2f}")
    return ", ".join(parts)


def clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def clamp_cash(value: float) -> float:
    return max(0.0, float(value))


def clamp_risk(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def build_initial_metrics(options: Iterable[Mapping[str, float]]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    count = 0
    for metrics in options:
        count += 1
        for name, value in metrics.items():
            totals[name] = totals.get(name, 0.0) + float(value)
    if count == 0:
        return {}
    return {name: clamp_metric(name, round(total / count, 2)) for name, total in totals.items()}


@dataclass
class DecisionState:
    """State snapshot for multi-step decisions."""

    scenario_id: str
    domain: str
    step_index: int
    metrics: Dict[str, float]
    context: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        metrics_text = summarize_metrics(self.metrics)
        return "\n".join(
            [
                f"Scenario ID: {self.scenario_id}",
                f"Domain: {self.domain}",
                f"Step: {self.step_index}",
                f"State metrics: {metrics_text}",
                f"Context: {self.context}",
            ]
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "domain": self.domain,
            "step_index": self.step_index,
            "metrics": dict(self.metrics),
            "context": self.context,
            "metadata": dict(self.metadata),
        }


@dataclass
class StateTransition:
    """Transition produced by applying an action to a state."""

    previous_state: DecisionState
    next_state: DecisionState
    action_label: str
    metrics_delta: Dict[str, float]
    terminated: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "previous_state": self.previous_state.as_dict(),
            "next_state": self.next_state.as_dict(),
            "action_label": self.action_label,
            "metrics_delta": dict(self.metrics_delta),
            "terminated": self.terminated,
            "metadata": dict(self.metadata),
        }


@dataclass
class LongHorizonState:
    step_index: int
    market_share: float
    cash: float
    product_quality: float
    marketing_strength: float
    competitor_strength: float
    reputation: float
    innovation: float
    risk_level: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "step_index": self.step_index,
            "market_share": self.market_share,
            "cash": self.cash,
            "product_quality": self.product_quality,
            "marketing_strength": self.marketing_strength,
            "competitor_strength": self.competitor_strength,
            "reputation": self.reputation,
            "innovation": self.innovation,
            "risk_level": self.risk_level,
        }
