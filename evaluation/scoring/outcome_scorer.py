"""
Outcome Scorer - Evaluates decision quality against rubrics

CRITICAL: Rule-based, deterministic scoring with ZERO LLM calls.

Scoring uses keyword matching and structural pattern matching only.
No LLM evaluation → No circular reasoning.
100% reproducible across runs.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import json
import re


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


# DETERMINISTIC PRINCIPLE KEYWORDS
# Each principle has explicit keyword list (no fuzzy matching)
PRINCIPLE_KEYWORDS = {
    "optionality": {
        "keywords": ["option", "options", "optionality", "flexibility", "flexible", "preserve", 
                    "choice", "choices", "alternatives", "paths", "path", "keep", "maintain"],
        "negations": [],
        "weight": 1.0
    },
    "downside_asymmetry": {
        "keywords": ["protect", "protection", "downside", "asymmetry", "asymmetric", "limited", 
                    "limit", "cap", "bound", "bounded", "hedge", "hedging"],
        "negations": [],
        "weight": 1.0
    },
    "reversibility": {
        "keywords": ["reverse", "reversible", "reversibility", "undo", "undoable", "trial", 
                    "test", "temporary", "provisional", "experiment", "pilot"],
        "negations": ["irreversible"],
        "weight": 1.0
    },
    "feedback_loops": {
        "keywords": ["feedback", "feedback loop", "learn", "learning", "iterate", "iteration", 
                    "adjust", "signal", "signals", "information"],
        "negations": [],
        "weight": 0.9
    },
    "systemic_barriers": {
        "keywords": ["systemic", "barrier", "barriers", "structural", "structure", "culture", 
                    "system", "lock", "locked", "constraint"],
        "negations": [],
        "weight": 0.9
    },
    "time_value": {
        "keywords": ["time", "timing", "wait", "waiting", "defer", "deferral", "temporal", 
                    "now", "later", "patience"],
        "negations": [],
        "weight": 1.0
    },
    "information_value": {
        "keywords": ["information", "informed", "uncertainty", "uncertain", "signal", "signals", 
                    "data", "evidence", "learn", "learning"],
        "negations": [],
        "weight": 0.9
    }
}


class OutcomeScorer:
    """
    Deterministic, rule-based scorer with NO LLM calls.
    
    Scoring rules are explicit and reproducible.
    """
    
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
        
        RULE-BASED ONLY: No LLM calls. Keyword matching only.
        
        Args:
            scenario_id: e.g., "IRR_001"
            category: e.g., "irreversible"
            decision_path: The chosen path taken
            decision_rationale: Decision explanation (text only)
            ground_truth_rubric: {"principles_required": [...], "acceptable_paths": [...]}
        
        Returns:
            RubricEvaluation with success/failure and scoring breakdown
        """
        
        # Rule 1: Check if acceptable path was taken
        acceptable_paths = ground_truth_rubric.get("acceptable_paths", [])
        path_matched = self._check_path_match(decision_path, acceptable_paths)
        matched_path_name = decision_path if path_matched else "MISMATCH"
        
        # Rule 2: Check principles using keyword matching
        required_principles = ground_truth_rubric.get("principles_required", [])
        principles_satisfied = self._extract_principles_rule_based(
            decision_rationale, 
            required_principles
        )
        principles_violated = [p for p in required_principles if p not in principles_satisfied]
        
        # Rule 3: Compute score using explicit weighted formula
        path_score = 1.0 if path_matched else 0.5
        
        if required_principles:
            principle_score = len(principles_satisfied) / len(required_principles)
        else:
            principle_score = 1.0
        
        # Scoring formula: 60% path matching, 40% principle coverage
        final_score = path_score * 0.6 + principle_score * 0.4
        
        # Rule 4: Determine success (strict: both path and all principles)
        success = path_matched and len(principles_violated) == 0
        
        evaluation = RubricEvaluation(
            scenario_id=scenario_id,
            category=category,
            success=success,
            principles_satisfied=principles_satisfied,
            principles_violated=principles_violated,
            acceptable_path_matched=matched_path_name,
            score=final_score,
            justification=self._build_justification(
                path_matched, 
                len(principles_satisfied), 
                len(required_principles)
            )
        )
        
        self.results.append(evaluation)
        return evaluation
    
    def _check_path_match(self, decision_path: str, acceptable_paths: List[str]) -> bool:
        """
        Check if decision_path matches any acceptable path.
        
        Rule: Exact string match (case-insensitive).
        """
        if not decision_path or not acceptable_paths:
            return False
        
        decision_lower = decision_path.lower().strip()
        
        for path in acceptable_paths:
            if path.lower().strip() == decision_lower:
                return True
        
        return False
    
    def _extract_principles_rule_based(
        self,
        text: str,
        required_principles: List[str]
    ) -> List[str]:
        """
        Extract principles using RULE-BASED keyword matching.
        
        ZERO LLM calls. Deterministic.
        
        Rule: A principle is satisfied if:
        - At least ONE keyword from its keyword list appears in text
        - AND the principle is NOT negated by negation keywords
        """
        if not text or not required_principles:
            return []
        
        text_lower = text.lower()
        found_principles = []
        
        for principle in required_principles:
            if principle not in PRINCIPLE_KEYWORDS:
                # Unknown principle - skip
                continue
            
            spec = PRINCIPLE_KEYWORDS[principle]
            keywords = spec["keywords"]
            negations = spec["negations"]
            
            # Check if any keyword appears
            keyword_found = any(kw in text_lower for kw in keywords)
            
            if not keyword_found:
                continue
            
            # Check negations (don't mark principle if negated)
            is_negated = any(neg in text_lower for neg in negations)
            
            if not is_negated:
                found_principles.append(principle)
        
        return found_principles
    
    def _build_justification(
        self,
        path_matched: bool,
        principles_count: int,
        required_count: int
    ) -> str:
        """Build human-readable justification string."""
        path_status = "✓" if path_matched else "✗"
        principle_status = f"{principles_count}/{required_count}"
        
        return f"Path: {path_status}, Principles: {principle_status}"
    
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
