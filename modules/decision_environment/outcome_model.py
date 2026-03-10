"""Outcome models for simulated decision environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List


@dataclass
class Outcome:
    profit: float
    market_share: float
    risk: float
    reputation: float
    cost: float
    confidence: float
    notes: List[str] = field(default_factory=list)


class OutcomeModel:
    def predict(self, scenario: Dict[str, Any], decision: str) -> Outcome:
        raise NotImplementedError


class RuleOutcomeModel(OutcomeModel):
    """Deterministic heuristic outcome model for fast simulation."""

    def predict(self, scenario: Dict[str, Any], decision: str) -> Outcome:
        text = str(decision or "").lower()
        context = scenario.get("context") or {}

        profit = 0.0
        market_share = 0.0
        risk = 0.0
        reputation = 0.0
        cost = 0.0
        notes: List[str] = []

        cash = float(context.get("cash_reserve_months", 12) or 12)
        time_pressure = float(context.get("time_pressure_days", 30) or 30)

        if "price" in text or "discount" in text:
            profit -= 0.2
            market_share += 0.15
            risk += 0.1
            cost += 0.1
            notes.append("price_cut")

        if "premium" in text or "differentiat" in text:
            profit += 0.12
            market_share += 0.05
            risk += 0.05
            notes.append("differentiation")

        if "marketing" in text or "campaign" in text:
            market_share += 0.12
            cost += 0.12
            risk += 0.05
            notes.append("marketing_spend")

        if "reliability" in text or "infrastructure" in text or "stability" in text:
            profit += 0.05
            risk -= 0.12
            reputation += 0.12
            cost += 0.05
            notes.append("reliability_investment")

        if "layoff" in text or "pay cut" in text or "freeze" in text:
            profit += 0.08
            reputation -= 0.15
            risk += 0.1
            notes.append("morale_hit")

        if "partner" in text or "joint" in text:
            market_share += 0.08
            risk -= 0.05
            notes.append("partnering")

        if "delay" in text or "pause" in text:
            profit -= 0.05
            risk += 0.08
            reputation -= 0.02
            notes.append("delay")

        if cash < 8:
            cost += 0.08
            risk += 0.05
            notes.append("low_runway")

        if time_pressure <= 14:
            risk += 0.05
            notes.append("time_pressure")

        return Outcome(
            profit=_clamp(profit),
            market_share=_clamp(market_share),
            risk=_clamp(risk),
            reputation=_clamp(reputation),
            cost=_clamp(cost),
            confidence=_clamp(0.6 + 0.05 * len(notes)),
            notes=notes,
        )


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, round(value, 4)))
