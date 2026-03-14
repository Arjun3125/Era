"""Minimal council aggregation utilities for compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass
class CouncilRecommendation:
    decision: str
    confidence: float = 0.5
    support_ratio: float = 0.5
    dissent_level: float = 0.0


class CouncilAggregator:
    """Simple weighted majority aggregator used in tests and legacy paths."""

    def aggregate(self, votes: Iterable[Dict[str, float]]) -> CouncilRecommendation:
        totals: Dict[str, float] = {}
        count = 0
        for vote in votes:
            count += 1
            for decision, weight in vote.items():
                totals[decision] = totals.get(decision, 0.0) + float(weight)

        if not totals:
            return CouncilRecommendation(decision="defer", confidence=0.0, support_ratio=0.0, dissent_level=0.0)

        best_decision = max(totals.items(), key=lambda x: x[1])[0]
        total_weight = sum(totals.values()) or 1.0
        support_ratio = totals[best_decision] / total_weight
        dissent_level = 1.0 - support_ratio
        confidence = min(0.95, 0.5 + support_ratio / 2.0)

        return CouncilRecommendation(
            decision=best_decision,
            confidence=confidence,
            support_ratio=support_ratio,
            dissent_level=dissent_level,
        )

    def aggregate_strings(self, recommendations: Iterable[str]) -> CouncilRecommendation:
        votes: List[Dict[str, float]] = [{rec: 1.0} for rec in recommendations]
        return self.aggregate(votes)


__all__ = ["CouncilAggregator", "CouncilRecommendation"]
