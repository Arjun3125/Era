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
import os
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class RubricEvaluation:
    """Result of rubric-based evaluation"""
    scenario_id: str
    category: str
    success: bool
    principles_satisfied: List[str]
    principles_violated: List[str]
    failure_modes_matched: List[str]
    failure_modes_avoided: List[str]
    acceptable_path_matched: str
    path_matched: bool
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

# Broader semantic proxies used in semantic/hybrid evaluator mode.
SEMANTIC_PRINCIPLE_PATTERNS = {
    "optionality": [r"\boption\w*\b", r"\bflexib\w*\b", r"\balternative\w*\b", r"\bpreserv\w*\b"],
    "downside_asymmetry": [r"\bdownside\b", r"\brisk\b", r"\bharm\b", r"\bworst[- ]case\b", r"\bprotect\w*\b"],
    "reversibility": [r"\brevers\w*\b", r"\bundo\w*\b", r"\btrial\b", r"\bpilot\b", r"\btemporary\b"],
    "feedback_loops": [r"\bfeedback\b", r"\biterate\w*\b", r"\blearn\w*\b", r"\bsecond[- ]order\b"],
    "systemic_barriers": [r"\bsystem\w*\b", r"\bstructur\w*\b", r"\bconstraint\w*\b", r"\bbarrier\w*\b", r"\bopposition\b", r"\bcompliance\b"],
    "time_value": [r"\btime\b", r"\btiming\b", r"\bwait\w*\b", r"\bdelay\w*\b", r"\bnow\b", r"\blater\b"],
    "information_value": [r"\binformation\b", r"\buncertain\w*\b", r"\bsignal\w*\b", r"\bevidence\b", r"\bdata\b", r"\blearn\w*\b"],
    # Additional rubric principles seen in dataset.
    "customer_trust": [r"\bcustomer\b", r"\btrust\b", r"\breputation\b"],
    "compliance": [r"\bcompliance\b", r"\bregulat\w*\b", r"\blegal\b"],
    "integrity": [r"\bintegrit\w*\b", r"\bethic\w*\b", r"\bhonest\w*\b"],
    "long_term_trust": [r"\blong[- ]term\b", r"\btrust\b", r"\breputation\b"],
    "information_hazard_control": [r"\binformation hazard\b", r"\bleak\w*\b", r"\bcontain\w*\b", r"\bsecurity\b"],
    "risk_management": [r"\brisk\b", r"\bmitigat\w*\b", r"\bcontingenc\w*\b", r"\bprotect\w*\b"],
    "fairness": [r"\bfair\w*\b", r"\bequit\w*\b", r"\bbias\b"],
    "long_term_quality": [r"\blong[- ]term\b", r"\bquality\b", r"\bdurable\b", r"\brobust\b"],
}


class OutcomeScorer:
    """
    Deterministic, rule-based scorer with NO LLM calls.
    
    Scoring rules are explicit and reproducible.
    """
    
    def __init__(self):
        self.results = []
        self.principle_match_mode = str(os.getenv("EVAL_PRINCIPLE_MATCH_MODE", "strict")).strip().lower()
    
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
        principles_satisfied = self._extract_principles(
            decision_rationale,
            required_principles,
        )
        principles_violated = [p for p in required_principles if p not in principles_satisfied]
        critical_failure_modes = ground_truth_rubric.get("critical_failure_modes", [])
        failure_modes_matched = self._match_failure_modes(
            decision_rationale, critical_failure_modes
        )
        failure_modes_avoided = [m for m in critical_failure_modes if m not in failure_modes_matched]
        
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
            failure_modes_matched=failure_modes_matched,
            failure_modes_avoided=failure_modes_avoided,
            acceptable_path_matched=matched_path_name,
            path_matched=path_matched,
            score=final_score,
            justification=self._build_justification(
                path_matched, 
                len(principles_satisfied), 
                len(required_principles)
            )
        )
        logger.info(
            "SCORER scenario=%s mode=%s path_matched=%s principles_matched=%s failure_modes_matched=%s",
            scenario_id,
            self.principle_match_mode,
            path_matched,
            principles_satisfied,
            failure_modes_matched,
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

    @staticmethod
    def _principle_name_token_match(text_lower: str, principle: str) -> bool:
        """
        Fallback semantic proxy for unknown principles: match normalized principle tokens
        (excluding ultra-short tokens) in rationale text.
        """
        tokens = [t for t in str(principle).lower().replace("-", "_").split("_") if len(t) >= 4]
        if not tokens:
            return False
        hits = sum(1 for t in tokens if t in text_lower)
        return hits >= max(1, len(tokens) // 2)

    def _extract_principles_semantic(
        self,
        text: str,
        required_principles: List[str],
    ) -> List[str]:
        """
        Semantic proxy matcher (still deterministic/no-LLM):
        - strict keyword matching first
        - broader regex patterns for paraphrases
        - fallback token overlap for unknown principle names
        """
        if not text or not required_principles:
            return []
        text_lower = text.lower()
        found: List[str] = []
        for principle in required_principles:
            p = str(principle)
            if p in found:
                continue
            # Keep strict behavior as a subset of semantic mode.
            strict_hit = p in self._extract_principles_rule_based(text, [p])
            if strict_hit:
                found.append(p)
                continue
            patterns = SEMANTIC_PRINCIPLE_PATTERNS.get(p, [])
            if any(re.search(pattern, text_lower) for pattern in patterns):
                found.append(p)
                continue
            if self._principle_name_token_match(text_lower, p):
                found.append(p)
        return found

    def _extract_principles(
        self,
        text: str,
        required_principles: List[str],
    ) -> List[str]:
        mode = self.principle_match_mode
        if mode in {"semantic", "soft", "fuzzy"}:
            return self._extract_principles_semantic(text, required_principles)
        if mode in {"hybrid"}:
            strict = self._extract_principles_rule_based(text, required_principles)
            semantic = self._extract_principles_semantic(text, required_principles)
            merged: List[str] = []
            for p in required_principles:
                if p in strict or p in semantic:
                    merged.append(p)
            return merged
        # default strict
        return self._extract_principles_rule_based(text, required_principles)
    
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

    def _match_failure_modes(self, text: str, failure_modes: List[str]) -> List[str]:
        """
        Match critical failure mode mentions in rationale text.
        Rule-based only: string containment after underscore->space normalization.
        """
        if not text or not failure_modes:
            return []
        text_lower = text.lower()
        matched = []
        for mode in failure_modes:
            mode_variant = mode.lower()
            mode_spaced = mode_variant.replace("_", " ")
            if mode_variant in text_lower or mode_spaced in text_lower:
                matched.append(mode)
        return matched
    
    def get_results_summary(self) -> Dict:
        """Aggregate scoring results"""
        if not self.results:
            return {"total_scenarios": 0, "pass_rate": 0.0}
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        avg_score = sum(r.score for r in self.results) / total
        path_detected = sum(1 for r in self.results if r.path_matched)
        total_failure_modes = sum(
            len(r.failure_modes_matched) + len(r.failure_modes_avoided) for r in self.results
        )
        matched_failure_modes = sum(len(r.failure_modes_matched) for r in self.results)
        failure_mode_match_rate = (
            matched_failure_modes / total_failure_modes if total_failure_modes > 0 else 0.0
        )
        
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
            "principle_match_mode": self.principle_match_mode,
            "pass_rate": passed / total,
            "mean_score": avg_score,
            "decision_path_detection_success_rate": path_detected / total,
            "failure_mode_match_rate": failure_mode_match_rate,
            "by_category": category_summary,
            "results": [
                {
                    "id": r.scenario_id,
                    "success": r.success,
                    "score": r.score,
                    "category": r.category,
                    "path_matched": r.path_matched,
                    "principles_satisfied": r.principles_satisfied,
                    "failure_modes_matched": r.failure_modes_matched,
                }
                for r in self.results
            ]
        }
