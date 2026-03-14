"""Risk scoring from uncertainty signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class RiskModel:
    policy_weight: float = 0.4
    value_weight: float = 0.3
    dissent_weight: float = 0.3

    def score(
        self,
        policy_entropy: float | None = None,
        value_variance: float | None = None,
        dissent_level: float | None = None,
    ) -> float:
        policy = float(policy_entropy or 0.0)
        value = float(value_variance or 0.0)
        dissent = float(dissent_level or 0.0)
        total = self.policy_weight + self.value_weight + self.dissent_weight
        if total <= 0:
            return 0.0
        risk = (
            self.policy_weight * policy
            + self.value_weight * value
            + self.dissent_weight * dissent
        ) / total
        return round(max(0.0, min(1.0, risk)), 4)

    def score_from_context(self, context: Mapping[str, float]) -> float:
        return self.score(
            policy_entropy=context.get("policy_entropy"),
            value_variance=context.get("value_variance"),
            dissent_level=context.get("dissent_level"),
        )
