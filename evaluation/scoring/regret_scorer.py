"""
Regret Scorer - Quantifies decision regret on calibrated scale

Implements regret scoring aligned with rubric severity levels.
No side effects on live system.
"""

from typing import Dict
from dataclasses import dataclass


@dataclass
class RegretScore:
    """Regret measurement for a decision"""
    scenario_id: str
    decision_path: str
    actual_outcome: str  # What actually happened
    optimal_path: str    # What should have happened
    regret_magnitude: float  # 0.0-1.0
    regret_category: str  # "catastrophic", "moderate", "minimal"
    explanation: str


class RegretScorer:
    """Score regret magnitude for decisions made"""
    
    def __init__(self):
        self.scores = []
    
    def score_regret(
        self,
        scenario_id: str,
        category: str,
        decision_path: str,
        actual_outcome: str,
        ground_truth_rubric: Dict,
        acceptable_paths: list = None
    ) -> RegretScore:
        """
        Score the regret of a decision based on outcome.
        
        Args:
            scenario_id: e.g., "IRR_001"
            category: Decision category
            decision_path: Path actually taken
            actual_outcome: Resulting outcome description
            ground_truth_rubric: Contains acceptable_paths and failure_modes
            acceptable_paths: Valid paths for this scenario
        
        Returns:
            RegretScore with magnitude and category
        """
        
        acceptable = acceptable_paths or ground_truth_rubric.get("acceptable_paths", [])
        critical_failures = ground_truth_rubric.get("critical_failure_modes", [])
        regret_scale = ground_truth_rubric.get("regret_scale", {
            "catastrophic": 1.0,
            "moderate": 0.5,
            "minimal": 0.1
        })
        
        # Check if path was acceptable
        is_acceptable = decision_path in acceptable
        
        # Check for critical failures
        has_critical_failure = any(
            failure.lower() in actual_outcome.lower()
            for failure in critical_failures
        )
        
        # Determine regret category
        if has_critical_failure:
            regret_category = "catastrophic"
            magnitude = regret_scale.get("catastrophic", 1.0)
            explanation = f"Critical failure detected: {actual_outcome}"
        elif not is_acceptable:
            regret_category = "moderate"
            magnitude = regret_scale.get("moderate", 0.5)
            explanation = f"Suboptimal path chosen: {decision_path}"
        else:
            regret_category = "minimal"
            magnitude = regret_scale.get("minimal", 0.1)
            explanation = f"Acceptable path taken: {decision_path}"
        
        score = RegretScore(
            scenario_id=scenario_id,
            decision_path=decision_path,
            actual_outcome=actual_outcome,
            optimal_path=acceptable[0] if acceptable else "UNKNOWN",
            regret_magnitude=magnitude,
            regret_category=regret_category,
            explanation=explanation
        )
        
        self.scores.append(score)
        return score
    
    def get_summary(self) -> Dict:
        """Summarize regret scores"""
        if not self.scores:
            return {"total": 0, "avg_regret": 0.0}
        
        total = len(self.scores)
        avg_regret = sum(s.regret_magnitude for s in self.scores) / total
        
        by_category = {}
        for score in self.scores:
            cat = score.regret_category
            if cat not in by_category:
                by_category[cat] = 0
            by_category[cat] += 1
        
        return {
            "total_scored": total,
            "avg_regret_magnitude": avg_regret,
            "catastrophic_count": by_category.get("catastrophic", 0),
            "moderate_count": by_category.get("moderate", 0),
            "minimal_count": by_category.get("minimal", 0),
            "percentile_catastrophic": (by_category.get("catastrophic", 0) / total * 100) if total > 0 else 0
        }
