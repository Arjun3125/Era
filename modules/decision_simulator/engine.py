"""Heuristic decision simulator for benchmark scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class OutcomePrediction:
    option: str
    benefit: float
    risk: float
    cost: float
    reversibility: float
    confidence: float
    notes: List[str] = field(default_factory=list)


@dataclass
class UtilityResult:
    option: str
    utility: float
    prediction: OutcomePrediction


class DecisionSimulator:
    """Deterministic heuristic simulator for option outcomes and utility."""

    def __init__(self) -> None:
        self._category_weights = {
            "strategy": {"benefit": 0.6, "risk": 0.3, "cost": 0.2, "reversibility": 0.2},
            "risk": {"benefit": 0.2, "risk": 0.8, "cost": 0.2, "reversibility": 0.2},
            "ethics": {"benefit": 0.4, "risk": 0.5, "cost": 0.2, "reversibility": 0.1},
            "resource_allocation": {"benefit": 0.6, "risk": 0.4, "cost": 0.3, "reversibility": 0.2},
            "long_term_tradeoffs": {"benefit": 0.5, "risk": 0.4, "cost": 0.2, "reversibility": 0.3},
        }

    def choose_best(self, scenario: Dict[str, Any]) -> UtilityResult:
        utilities = self.compute_utilities(scenario)
        return max(utilities, key=lambda item: item.utility)

    def compute_utilities(self, scenario: Dict[str, Any]) -> List[UtilityResult]:
        category = str(scenario.get("category", "strategy")).strip().lower()
        weights = self._category_weights.get(category, self._category_weights["strategy"])
        options = scenario.get("decision_options") or []
        outputs: List[UtilityResult] = []
        for option in options:
            prediction = self.predict_outcome(scenario, option)
            utility = (
                weights["benefit"] * prediction.benefit
                - weights["risk"] * prediction.risk
                - weights["cost"] * prediction.cost
                + weights["reversibility"] * prediction.reversibility
            )
            outputs.append(
                UtilityResult(
                    option=str(option),
                    utility=round(utility, 4),
                    prediction=prediction,
                )
            )
        return outputs

    def reasoning_hints(self, scenario: Dict[str, Any], prediction: OutcomePrediction | None) -> List[str]:
        if prediction is None:
            return []
        category = str(scenario.get("category", "strategy")).strip().lower()
        hints: List[str] = []
        for note in prediction.notes:
            if category == "risk":
                if note == "mitigate_risk":
                    hints.append("reduce single point of failure")
                if note == "time_pressure":
                    hints.append("preserve delivery commitments")
                if note == "low_runway":
                    hints.append("control costs")
                if note == "compliance":
                    hints.append("regulatory compliance")
            elif category == "resource_allocation":
                if note == "resilience_investment":
                    hints.append("protect uptime")
                if note == "balanced_allocation":
                    hints.append("align with stage")
                if note == "growth_spend":
                    hints.append("support growth")
            elif category == "strategy":
                if note == "price_war":
                    hints.append("avoid destructive price war")
                if note == "growth_spend":
                    hints.append("increase product differentiation")
            elif category == "ethics":
                if note == "compliance":
                    hints.append("transparency")
                if note == "morale_risk":
                    hints.append("treat people fairly")
            elif category == "long_term_tradeoffs":
                if note == "resilience_investment":
                    hints.append("sustain trust")
                if note == "balanced_allocation":
                    hints.append("retain optionality")

        # Deduplicate while preserving order.
        seen = set()
        deduped: List[str] = []
        for item in hints:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def predict_outcome(self, scenario: Dict[str, Any], option: str) -> OutcomePrediction:
        text = str(option).strip().lower()
        context = scenario.get("context") or {}
        cash_months = float(context.get("cash_reserve_months", 12) or 12)
        time_pressure = float(context.get("time_pressure_days", 30) or 30)

        benefit = 0.5
        risk = 0.5
        cost = 0.5
        reversibility = 0.5
        notes: List[str] = []

        if any(token in text for token in ["delay", "defer", "wait", "pause", "monitor"]):
            benefit -= 0.15
            risk += 0.2
            reversibility += 0.2
            notes.append("delay")

        if any(token in text for token in ["dual-source", "redundant", "backup", "mitigation", "harden"]):
            risk -= 0.3
            cost += 0.1
            benefit += 0.15
            notes.append("mitigate_risk")

        if any(token in text for token in ["increase marketing", "marketing", "sales-heavy", "growth"]):
            benefit += 0.15
            cost += 0.15
            risk += 0.05
            notes.append("growth_spend")

        if any(token in text for token in ["lower price", "discount", "price"]):
            benefit += 0.1
            risk += 0.2
            cost += 0.2
            notes.append("price_war")

        if any(token in text for token in ["compliance", "disclosure", "transparency", "audit"]):
            risk -= 0.35
            cost += 0.05
            benefit += 0.1
            notes.append("compliance")

        if any(token in text for token in ["reliability-first", "reliability", "multi-cloud", "redundancy"]):
            benefit += 0.2
            risk -= 0.2
            cost += 0.1
            notes.append("resilience_investment")

        if any(token in text for token in ["balanced", "even split"]):
            benefit += 0.1
            risk -= 0.05
            cost += 0.05
            notes.append("balanced_allocation")

        if any(token in text for token in ["product-heavy", "sales-heavy"]):
            benefit += 0.05
            risk += 0.1
            cost += 0.1
            notes.append("focus_spend")

        if any(token in text for token in ["layoffs", "pay cuts", "freeze"]):
            cost -= 0.1
            risk += 0.2
            benefit -= 0.05
            notes.append("morale_risk")

        if cash_months < 12:
            cost += 0.1
            risk += 0.05
            notes.append("low_runway")

        if time_pressure <= 14:
            risk += 0.05
            reversibility -= 0.05
            notes.append("time_pressure")

        benefit = self._clamp(benefit)
        risk = self._clamp(risk)
        cost = self._clamp(cost)
        reversibility = self._clamp(reversibility)
        confidence = self._clamp(0.6 + (0.1 if notes else 0.0))

        return OutcomePrediction(
            option=str(option),
            benefit=benefit,
            risk=risk,
            cost=cost,
            reversibility=reversibility,
            confidence=confidence,
            notes=notes,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return round(value, 4)
