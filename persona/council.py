"""
Council Aggregator - Coordinates Minister outputs and produces consensus recommendations.

Aggregates individual minister stances into a coherent council recommendation
that Prime Confident can use for final decision-making.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from .ministers import MINISTERS, JUDGES, MinisterPosition
from .trace import trace


@dataclass
class CouncilRecommendation:
    """Aggregated recommendation from the council of ministers."""
    outcome: str  # "consensus_reached", "bounded_risk_tradeoff", "deadlocked"
    recommendation: str  # "support", "oppose", "defer"
    avg_confidence: float  # 0-1, average confidence across ministers
    reasoning: str
    minister_positions: Dict[str, MinisterPosition]
    consensus_strength: float  # 0-1, how strong the agreement is
    dissenting_ministers: List[str]
    red_line_concerns: List[str]
    judge_observations: Dict[str, MinisterPosition] = None  # Advisory observations from judges


class CouncilAggregator:
    """Gathers minister positions and produces consensus."""
    
    def __init__(self, llm=None):
        self.llm = llm
        # Initialize 19 voting ministers
        self.ministers: Dict[str, object] = {}
        for domain_name, MinisterClass in MINISTERS.items():
            self.ministers[domain_name] = MinisterClass(domain=domain_name, llm=llm)
        # Initialize judges (advisory, non-voting)
        self.judges: Dict[str, object] = {}
        for judge_name, JudgeClass in JUDGES.items():
            self.judges[judge_name] = JudgeClass(domain=judge_name, llm=llm)
    
    def convene(self, user_input: str, context: Dict[str, Any]) -> CouncilRecommendation:
        """
        Convene all ministers, collect their positions, and aggregate into a recommendation.
        
        Args:
            user_input: The user's input to analyze
            context: Conversation context (domains, recent_turns, etc.)
        
        Returns:
            CouncilRecommendation with aggregated stance, confidence, and outcomes
        """
        # Ensure context includes user_input for doctrine loading
        context["user_input"] = user_input
        
        minister_positions: Dict[str, MinisterPosition] = {}
        stances = {"support": [], "oppose": [], "neutral": []}
        confidences = []
        red_line_concerns = []
        doctrine_applied_count = 0
        
        # Get each minister's position (voting members only)
        for domain_name, minister in self.ministers.items():
            try:
                position = minister.analyze(user_input, context)
                minister_positions[domain_name] = position
                
                # Collect metrics
                stances[position.stance].append(domain_name)
                confidences.append(position.confidence)
                
                if position.red_line_triggered:
                    red_line_concerns.append(domain_name)
                
                if getattr(position, 'doctrine_applied', False):
                    doctrine_applied_count += 1
                
                trace("council_minister_position", {
                    "minister": domain_name,
                    "stance": position.stance,
                    "confidence": position.confidence,
                    "red_line": position.red_line_triggered,
                    "doctrine_applied": getattr(position, 'doctrine_applied', False)
                })
            except Exception as e:
                trace("council_minister_error", {
                    "minister": domain_name,
                    "error": str(e)
                })
                # Continue with other ministers even if one fails
                continue
        
        # Get judges' observations (advisory only, don't affect consensus)
        judge_positions: Dict[str, MinisterPosition] = {}
        for judge_name, judge in self.judges.items():
            try:
                position = judge.analyze(user_input, context)
                judge_positions[judge_name] = position
                trace("council_judge_observation", {
                    "judge": judge_name,
                    "stance": position.stance,
                    "confidence": position.confidence,
                    "note": "advisory only, not counted in consensus"
                })
            except Exception as e:
                trace("council_judge_error", {
                    "judge": judge_name,
                    "error": str(e)
                })
                continue
        
        # Compute aggregate metrics
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        total_ministers = len(minister_positions)
        
        support_count = len(stances["support"])
        oppose_count = len(stances["oppose"])
        neutral_count = len(stances["neutral"])
        
        # Determine consensus outcome and recommendation
        consensus_strength = 0.0
        outcome = "deadlocked"
        recommendation = "defer"
        reasoning_parts = []
        
        # Check for red lines first (auto-reject)
        if red_line_concerns:
            recommendation = "oppose"
            outcome = "consensus_reached"
            reasoning_parts.append(f"RED LINE triggered by: {', '.join(red_line_concerns)}")
            consensus_strength = 0.95
        # Strong support consensus
        elif support_count > oppose_count and support_count >= (total_ministers * 0.6):
            recommendation = "support"
            outcome = "consensus_reached"
            consensus_strength = support_count / total_ministers
            reasoning_parts.append(f"Support consensus: {support_count}/{total_ministers} ministers")
        # Strong oppose consensus
        elif oppose_count > support_count and oppose_count >= (total_ministers * 0.6):
            recommendation = "oppose"
            outcome = "consensus_reached"
            consensus_strength = oppose_count / total_ministers
            reasoning_parts.append(f"Oppose consensus: {oppose_count}/{total_ministers} ministers")
        # Bounded risk tradeoff (mixed signals but analyzable)
        elif support_count > 0 and oppose_count > 0:
            recommendation = "support_with_caution"
            outcome = "bounded_risk_tradeoff"
            consensus_strength = max(support_count, oppose_count) / total_ministers
            reasoning_parts.append(f"Mixed signals: {support_count} support, {oppose_count} oppose, {neutral_count} neutral")
            
            # Risk minister's concerns should be surfaced
            if "risk" in stances["oppose"]:
                reasoning_parts.append("Risk minister urges caution")
        # Deadlock
        else:
            outcome = "deadlocked"
            recommendation = "defer"
            consensus_strength = 0.0
            reasoning_parts.append(f"Deadlock: {support_count} support, {oppose_count} oppose, {neutral_count} neutral")
        
        dissenting_ministers = []
        if recommendation == "support":
            dissenting_ministers = stances["oppose"]
        elif recommendation == "oppose":
            dissenting_ministers = stances["support"]
        
        reasoning = " | ".join(reasoning_parts)
        
        trace("council_aggregation", {
            "outcome": outcome,
            "recommendation": recommendation,
            "avg_confidence": avg_confidence,
            "support": support_count,
            "oppose": oppose_count,
            "neutral": neutral_count,
            "consensus_strength": consensus_strength,
            "red_lines": red_line_concerns,
            "doctrine_applied_ministers": doctrine_applied_count,
            "judges_observing": list(judge_positions.keys())
        })
        
        return CouncilRecommendation(
            outcome=outcome,
            recommendation=recommendation,
            avg_confidence=avg_confidence,
            reasoning=reasoning,
            minister_positions=minister_positions,
            consensus_strength=consensus_strength,
            dissenting_ministers=dissenting_ministers,
            red_line_concerns=red_line_concerns,
            judge_observations=judge_positions
        )
