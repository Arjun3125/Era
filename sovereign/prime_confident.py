"""
Prime Confident runtime: final authority that merges council recommendations and provides final decision and rationale.

Loads doctrine from C:/era/data/doctrine/locked/n.yaml which defines:
- Role identity: Mirror with teeth, synthesis point for personal context
- Core worldview: Pattern recurrence, emotional distortion detection, self-deception prevention
- Self-constraints: Never decide alone, never moralize, never seek obedience
"""
import os
import sys
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.doctrine_loader import DoctrineLoader, DoctrinalCanon


class PrimeConfident:
    def __init__(self, risk_threshold: float = 0.7, llm_adapter: Optional[Any] = None):
        self.risk_threshold = float(risk_threshold)
        self.llm_adapter = llm_adapter
        # Load N's doctrine from YAML
        self.doctrine: Optional[DoctrinalCanon] = DoctrineLoader.load("n")
        if self.doctrine:
            self.canon_keywords = DoctrineLoader.extract_worldview_keywords(self.doctrine.canon_text)
            self.typical_warnings = DoctrineLoader.extract_warnings(self.doctrine.canon_text)
    
    def _analyze_emotional_distortion(self, council_rec: Dict[str, Any]) -> bool:
        """
        Per doctrine: Detect if decision is driven by emotional relief rather than problem-solving.
        This aligns with N's purpose: protect from self-deception under emotion, fatigue, or urgency.
        """
        # Check if confidence is artificially high (emotional relief) vs grounded in consensus
        avg_conf = council_rec.get("avg_confidence", 0.5)
        consensus_strength = council_rec.get("consensus_strength", 0.0)
        
        # If confidence is high but consensus is weak, likely emotional choice
        if avg_conf > 0.7 and consensus_strength < 0.3:
            return True  # Emotional distortion detected
        
        return False
    
    def _detect_pattern_recurrence(self, council_rec: Dict[str, Any]) -> bool:
        """
        Per doctrine: Detect recurring patterns that signal self-sabotage.
        N exists to identify "most damaging mistakes repeat with different justifications."
        """
        reasoning = council_rec.get("reasoning", "").lower()
        
        # Check for rationalization patterns
        rationalizations = ["but", "however", "despite", "still", "anyway", "regardless"]
        for rationalization in rationalizations:
            if reasoning.count(rationalization) > 2:
                return True  # Pattern of rationalization detected
        
        return False
    
    def _apply_doctrine_constraints(self, council_rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply N's self-constraint principles before deciding:
        - Never decide (validate consensus instead)
        - Never moralize (focus on consequences)
        - Never command (recommend, don't dictate)
        - Never replace Sovereign's agency (defer when unclear)
        """
        if not self.doctrine:
            return None
        
        # Check if this violates doctrine prohibitions
        prohibitions = [p.lower() for p in self.doctrine.prohibitions]
        
        # Example: If tendency to moralize detected, return recommendation to defer
        if any("must not moralize" in p for p in prohibitions):
            reasoning = council_rec.get("reasoning", "").lower()
            moral_words = ["should", "ought", "right", "wrong", "evil", "sin"]
            if any(word in reasoning for word in moral_words):
                return {
                    "constraint_violated": "moralization",
                    "recommendation": "defer",
                    "reason": "N's doctrine prohibits moralizing - focus on consequences instead"
                }
        
        return None
    
    def decide(self, council_recommendation: Dict[str, Any], minister_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Make final decision per N's doctrine: a mirror with teeth that protects the Sovereign
        from self-deception by exposing emotional distortion and pattern recurrence.
        """
        outcome = council_recommendation.get("outcome")
        result = {"final_outcome": "defer", "reason": "none"}

        # First: Check if doctrine constraints are violated
        constraint_check = self._apply_doctrine_constraints(council_recommendation)
        if constraint_check:
            return {
                "final_outcome": "defer",
                "reason": constraint_check.get("reason", "doctrine constraint"),
                "doctrine_constraint": constraint_check.get("constraint_violated")
            }
        
        # Second: Detect emotional distortion (per N's core worldview)
        if self._analyze_emotional_distortion(council_recommendation):
            result = {
                "final_outcome": "defer",
                "reason": "emotional_distortion_detected",
                "n_warning": "This solves the feeling, not the problem. Slow the decision."
            }
            return result
        
        # Third: Detect pattern recurrence (per N's core worldview)
        if self._detect_pattern_recurrence(council_recommendation):
            result = {
                "final_outcome": "defer",
                "reason": "pattern_recurrence_detected",
                "n_warning": "You've been here before. Different justification, same mistake."
            }
            return result
        
        # Fourth: Standard council evaluation (baseline logic)
        if outcome == "consensus_reached":
            if council_recommendation.get("recommendation") == "support" and council_recommendation.get("avg_confidence", 0.0) >= self.risk_threshold:
                result = {"final_outcome": "accept", "reason": "consensus_high_confidence", "details": council_recommendation}
            else:
                result = {"final_outcome": "defer", "reason": "consensus_low_confidence", "details": council_recommendation}
        elif outcome == "bounded_risk_tradeoff":
            risk_minister = minister_outputs.get("risk")
            if risk_minister:
                if risk_minister.get("red_line_triggered"):
                    return {"final_outcome": "reject", "reason": "risk_red_line", "minister": "risk", "n_warning": "Risk minister triggered red line. This has extinction-level stakes."}
                if risk_minister.get("stance") == "oppose" and float(risk_minister.get("confidence", 0)) >= self.risk_threshold:
                    return {"final_outcome": "defer", "reason": "risk_opposition_high_confidence", "minister": "risk"}
            if council_recommendation.get("avg_confidence", 0.0) >= self.risk_threshold:
                result = {"final_outcome": "accept_with_mitigation", "reason": "tradeoff_acceptable", "details": council_recommendation}
            else:
                result = {"final_outcome": "defer", "reason": "tradeoff_uncertain", "details": council_recommendation}
        else:
            result = {"final_outcome": "defer", "reason": "no_clear_recommendation", "details": council_recommendation}

        # Optionally augment decision with LLM assessment for richer rationale
        try:
            if self.llm_adapter:
                # Build compact text for assessment
                parts = [f"Recommendation: {council_recommendation.get('recommendation')}"]
                parts.append(f"Reasoning: {council_recommendation.get('reasoning', '')}")
                for d, m in minister_outputs.items():
                    parts.append(f"{d}: {m.get('stance')} ({m.get('confidence')})")
                text = "\n".join(parts)
                score, reason = self.llm_adapter.evaluate_viability(text)
                result["llm_assessment"] = {"score": float(score), "reason": reason}
        except Exception as e:
            # Non-fatal: record trace via DoctrineLoader
            try:
                from persona.trace import trace
                trace("prime_llm_assessment_error", {"error": str(e)})
            except Exception:
                pass

        return result
