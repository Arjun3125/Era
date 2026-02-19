"""
Outcome Scorer - Evaluates decision quality against rubrics

Rubric-based scoring for decision outcomes in isolated evaluation mode.
No side effects on live system.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import json


@dataclass
class RubricEvaluation:
    """Result of rubric-based evaluation"""
    scenario_id: str
    category: str
    success: bool
    principles_satisfied: List[str]
    principles_violated: List[str]
    acceptable_path_matched: str
    score: float  # 0.0-1.0
    justification: str


class OutcomeScorer:
    """Score decision outcomes against ground truth rubrics"""
    
    def __init__(self):
        self.results = []
    
    def evaluate_decision(
        self,
        scenario_id: str,
        category: str,
        decision_path: str,
        decision_rationale: str,
        ground_truth_rubric: Dict
    ) -> RubricEvaluation:
        """
        Score a decision against its ground truth rubric.
        
        Args:
            scenario_id: e.g., "IRR_001"
            category: e.g., "irreversible"
            decision_path: The chosen path taken
            decision_rationale: LLM rationale for the choice
            ground_truth_rubric: {"principles_required": [...], "acceptable_paths": [...]}
        
        Returns:
            RubricEvaluation with success/failure and scoring breakdown
        """
        
        # Check if acceptable path was taken
        acceptable_paths = ground_truth_rubric.get("acceptable_paths", [])
        path_matched = decision_path in acceptable_paths
        
        # Check principles
        required_principles = ground_truth_rubric.get("principles_required", [])
        principles_satisfied = self._extract_principles(decision_rationale, required_principles)
        principles_violated = [p for p in required_principles if p not in principles_satisfied]
        
        # Compute score
        path_score = 1.0 if path_matched else 0.5
        principle_score = len(principles_satisfied) / len(required_principles) if required_principles else 1.0
        
        success = path_matched and len(principles_violated) == 0
        final_score = (path_score * 0.6 + principle_score * 0.4) if required_principles else path_score
        
        evaluation = RubricEvaluation(
            scenario_id=scenario_id,
            category=category,
            success=success,
            principles_satisfied=principles_satisfied,
            principles_violated=principles_violated,
            acceptable_path_matched=decision_path if path_matched else "MISMATCH",
            score=final_score,
            justification=f"Path: {path_matched}, Principles: {len(principles_satisfied)}/{len(required_principles)}"
        )
        
        self.results.append(evaluation)
        return evaluation
    
    def _extract_principles(self, text: str, principles: List[str]) -> List[str]:
        """Check which principles are evident in the decision rationale"""
        text_lower = text.lower()
        found = []
        
        principle_keywords = {
            "optionality": ["option", "flexibility", "preserve", "choice"],
            "downside_asymmetry": ["protect", "limit loss", "downside", "asymmetry"],
            "reversibility": ["reverse", "undo", "trial", "test"],
            "feedback_loops": ["feedback", "learn", "iterate", "signal"],
            "systemic_barriers": ["systemic", "barrier", "structural", "culture"],
            "time_value": ["time", "timing", "wait", "defer"],
            "information_value": ["information", "learn", "uncertainty", "signal"],
            "optionality_time": ["timing", "option", "decision_tree"]
        }
        
        for principle in principles:
            keywords = principle_keywords.get(principle, [principle])
            if any(kw in text_lower for kw in keywords):
                found.append(principle)
        
        return found
    
    def get_results_summary(self) -> Dict:
        """Aggregate scoring results"""
        if not self.results:
            return {"total_scenarios": 0, "pass_rate": 0.0}
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        avg_score = sum(r.score for r in self.results) / total
        
        by_category = {}
        for result in self.results:
            cat = result.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0, "scores": []}
            by_category[cat]["total"] += 1
            if result.success:
                by_category[cat]["passed"] += 1
            by_category[cat]["scores"].append(result.score)
        
        category_summary = {}
        for cat, stats in by_category.items():
            category_summary[cat] = {
                "pass_rate": stats["passed"] / stats["total"],
                "mean_score": sum(stats["scores"]) / len(stats["scores"]),
                "count": stats["total"]
            }
        
        return {
            "total_scenarios": total,
            "pass_rate": passed / total,
            "mean_score": avg_score,
            "by_category": category_summary,
            "results": [
                {
                    "id": r.scenario_id,
                    "success": r.success,
                    "score": r.score,
                    "category": r.category
                }
                for r in self.results
            ]
        }
