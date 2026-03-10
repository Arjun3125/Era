"""Reward calculation for simulated outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .outcome_model import Outcome


@dataclass
class RewardConfig:
    profit_weight: float = 0.45
    market_share_weight: float = 0.2
    reputation_weight: float = 0.2
    risk_penalty: float = 0.35
    cost_penalty: float = 0.2


class RewardFunction:
    def __init__(self, config: RewardConfig | None = None) -> None:
        self.config = config or RewardConfig()

    def compute(self, outcome: Outcome) -> float:
        score = (
            self.config.profit_weight * outcome.profit
            + self.config.market_share_weight * outcome.market_share
            + self.config.reputation_weight * outcome.reputation
            - self.config.risk_penalty * outcome.risk
            - self.config.cost_penalty * outcome.cost
        )
        return max(-1.0, min(1.0, round(score, 4)))
