"""Package-local council aggregator compatibility layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..ministers import JUDGES, MINISTERS, MinisterPosition
from ..trace import trace


@dataclass
class CouncilRecommendation:
    """Aggregated recommendation from the council of ministers."""

    outcome: str
    recommendation: str
    avg_confidence: float
    reasoning: str
    minister_positions: Dict[str, MinisterPosition]
    consensus_strength: float
    dissenting_ministers: List[str]
    red_line_concerns: List[str]
    judge_observations: Optional[Dict[str, MinisterPosition]] = None


class CouncilAggregator:
    """Gathers minister positions and produces consensus."""

    def __init__(self, llm: Any = None):
        self.llm = llm
        self.ministers: Dict[str, object] = {}
        for domain_name, minister_class in MINISTERS.items():
            self.ministers[domain_name] = minister_class(domain=domain_name, llm=llm)
        self.judges: Dict[str, object] = {}
        for judge_name, judge_class in JUDGES.items():
            self.judges[judge_name] = judge_class(domain=judge_name, llm=llm)

    def convene(self, user_input: str, context: Dict[str, Any]) -> CouncilRecommendation:
        context = dict(context)
        context["user_input"] = user_input

        minister_positions: Dict[str, MinisterPosition] = {}
        stances = {"support": [], "oppose": [], "neutral": []}
        confidences: List[float] = []
        red_line_concerns: List[str] = []
        doctrine_applied_count = 0

        for domain_name, minister in self.ministers.items():
            try:
                position = minister.analyze(user_input, context)  # type: ignore[attr-defined]
                minister_positions[domain_name] = position
                stances[position.stance].append(domain_name)
                confidences.append(position.confidence)
                if position.red_line_triggered:
                    red_line_concerns.append(domain_name)
                if getattr(position, "doctrine_applied", False):
                    doctrine_applied_count += 1
                trace(
                    "council_minister_position",
                    {
                        "minister": domain_name,
                        "stance": position.stance,
                        "confidence": position.confidence,
                        "red_line": position.red_line_triggered,
                        "doctrine_applied": getattr(position, "doctrine_applied", False),
                    },
                )
            except Exception as exc:
                trace("council_minister_error", {"minister": domain_name, "error": str(exc)})
                continue

        judge_positions: Dict[str, MinisterPosition] = {}
        for judge_name, judge in self.judges.items():
            try:
                position = judge.analyze(user_input, context)  # type: ignore[attr-defined]
                judge_positions[judge_name] = position
                trace(
                    "council_judge_observation",
                    {
                        "judge": judge_name,
                        "stance": position.stance,
                        "confidence": position.confidence,
                        "note": "advisory only, not counted in consensus",
                    },
                )
            except Exception as exc:
                trace("council_judge_error", {"judge": judge_name, "error": str(exc)})
                continue

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        total_ministers = len(minister_positions)
        support_count = len(stances["support"])
        oppose_count = len(stances["oppose"])
        neutral_count = len(stances["neutral"])

        outcome = "deadlocked"
        recommendation = "defer"
        consensus_strength = 0.0
        reasoning_parts: List[str] = []

        if red_line_concerns:
            recommendation = "oppose"
            outcome = "consensus_reached"
            consensus_strength = 0.95
            reasoning_parts.append(f"RED LINE triggered by: {', '.join(red_line_concerns)}")
        elif support_count > oppose_count and support_count >= (total_ministers * 0.6):
            recommendation = "support"
            outcome = "consensus_reached"
            consensus_strength = support_count / total_ministers if total_ministers else 0.0
            reasoning_parts.append(f"Support consensus: {support_count}/{total_ministers} ministers")
        elif oppose_count > support_count and oppose_count >= (total_ministers * 0.6):
            recommendation = "oppose"
            outcome = "consensus_reached"
            consensus_strength = oppose_count / total_ministers if total_ministers else 0.0
            reasoning_parts.append(f"Oppose consensus: {oppose_count}/{total_ministers} ministers")
        elif support_count > 0 and oppose_count > 0:
            recommendation = "support_with_caution"
            outcome = "bounded_risk_tradeoff"
            consensus_strength = max(support_count, oppose_count) / total_ministers if total_ministers else 0.0
            reasoning_parts.append(
                f"Mixed signals: {support_count} support, {oppose_count} oppose, {neutral_count} neutral"
            )
            if "risk" in stances["oppose"]:
                reasoning_parts.append("Risk minister urges caution")
        else:
            outcome = "deadlocked"
            recommendation = "defer"
            consensus_strength = 0.0
            reasoning_parts.append(
                f"Deadlock: {support_count} support, {oppose_count} oppose, {neutral_count} neutral"
            )

        dissenting_ministers: List[str] = []
        if recommendation == "support":
            dissenting_ministers = stances["oppose"]
        elif recommendation == "oppose":
            dissenting_ministers = stances["support"]

        reasoning = " | ".join(reasoning_parts)
        trace(
            "council_aggregation",
            {
                "outcome": outcome,
                "recommendation": recommendation,
                "avg_confidence": avg_confidence,
                "support": support_count,
                "oppose": oppose_count,
                "neutral": neutral_count,
                "consensus_strength": consensus_strength,
                "red_lines": red_line_concerns,
                "doctrine_applied_ministers": doctrine_applied_count,
                "judges_observing": list(judge_positions.keys()),
            },
        )

        return CouncilRecommendation(
            outcome=outcome,
            recommendation=recommendation,
            avg_confidence=avg_confidence,
            reasoning=reasoning,
            minister_positions=minister_positions,
            consensus_strength=consensus_strength,
            dissenting_ministers=dissenting_ministers,
            red_line_concerns=red_line_concerns,
            judge_observations=judge_positions,
        )
