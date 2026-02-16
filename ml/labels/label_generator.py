"""
Label Generation for ML Judgment Learning

Converts decision outcomes into training labels that tell the ML model
"What kind of knowledge should have mattered more or less in situations like this?"

This mirrors how humans learn judgment: from consequences, not advice.
"""

import math
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class TypeWeights:
    """Knowledge type importance weights (labels)."""
    principle_weight: float = 1.0
    rule_weight: float = 1.0
    warning_weight: float = 1.0
    claim_weight: float = 1.0
    advice_weight: float = 1.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "principle_weight": self.principle_weight,
            "rule_weight": self.rule_weight,
            "warning_weight": self.warning_weight,
            "claim_weight": self.claim_weight,
            "advice_weight": self.advice_weight,
        }
    
    def to_list(self) -> List[float]:
        """Ordered list for ML training."""
        return [
            self.principle_weight,
            self.rule_weight,
            self.warning_weight,
            self.claim_weight,
            self.advice_weight,
        ]


def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value to bounds."""
    return max(lo, min(hi, x))


def interpret_outcome(outcome: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collapse raw outcome into judgment signals.
    
    Extracts:
    - success (bool)
    - regret (0–1)
    - recovery_time_long (bool)
    - secondary_damage (bool)
    """
    return {
        "success": outcome.get("success", False),
        "regret": clamp(outcome.get("regret_score", 0.0), 0.0, 1.0),
        "recovery_long": outcome.get("recovery_time_days", 0) > 90,
        "secondary_damage": outcome.get("secondary_damage", False),
    }


def assess_severity(
    situation_features: Dict[str, float],
    constraint_features: Dict[str, float]
) -> float:
    """
    Compute severity of the decision situation.
    
    Severity determines how strongly learning signals propagate.
    
    High severity → stronger corrections
    Low severity → gentle adjustments
    """
    severity = 0.0
    
    # Irreversibility dominates
    severity += 0.4 * constraint_features.get("irreversibility_score", 0.0)
    
    # Asymmetry matters
    severity += 0.3 * constraint_features.get("downside_asymmetry", 0.0)
    
    # Fragility amplifies
    severity += 0.2 * constraint_features.get("fragility_score", 0.0)
    
    # Time pressure adds pressure
    severity += 0.1 * situation_features.get("time_pressure", 0.0)
    
    return clamp(severity, 0.0, 1.0)


def summarize_knowledge_usage(knowledge_features: Dict[str, float]) -> Dict[str, bool]:
    """
    Summarize which knowledge types were used in the decision.
    """
    return {
        "principle": knowledge_features.get("used_principle", 0.0) > 0.5,
        "rule": knowledge_features.get("used_rule", 0.0) > 0.5,
        "warning": knowledge_features.get("used_warning", 0.0) > 0.5,
        "claim": knowledge_features.get("used_claim", 0.0) > 0.5,
        "advice": knowledge_features.get("used_advice", 0.0) > 0.5,
    }


def generate_type_weights(
    situation_features: Dict[str, float],
    constraint_features: Dict[str, float],
    knowledge_features: Dict[str, float],
    outcome: Dict[str, Any]
) -> TypeWeights:
    """
    CORE LOGIC: Generate type-weight corrections from decision outcome.
    
    This is where human learning patterns are encoded.
    
    Rules:
    1. Failure + irreversibility → ↑ warnings, principles
    2. Failure + rules → ↓ rules
    3. Advice + regret → ↓ advice
    4. Success + recovery → ↑ principles
    5. Execution + success → ↑ rules
    
    All adjustments are bounded [0.7, 1.3] to prevent extreme oscillation.
    """
    
    # Start neutral
    weights = TypeWeights()
    
    # Interpret outcomes
    interpreted_outcome = interpret_outcome(outcome)
    
    # Assess severity (high severity = stronger learning)
    severity = assess_severity(situation_features, constraint_features)
    
    # Summarize what was used
    used = summarize_knowledge_usage(knowledge_features)
    
    # ====================================================================
    # FAILURE-BASED LEARNING
    # ====================================================================
    if not interpreted_outcome["success"]:
        
        # High irreversibility + failure → warnings/principles underweighted
        if constraint_features.get("irreversibility_score", 0.0) > 0.7:
            weights.warning_weight += 0.3 * severity
            weights.principle_weight += 0.2 * severity
        
        # Rule-heavy execution in irreversible case → rules overweighted
        if used["rule"] and situation_features.get("decision_irreversible", 0.0) > 0.5:
            weights.rule_weight -= 0.2 * severity
        
        # Advice-led failures → advice unreliable here
        if used["advice"]:
            weights.advice_weight -= 0.3 * severity
        
        # Low information + failure → claims didn't help
        if constraint_features.get("information_completeness", 1.0) < 0.5:
            weights.claim_weight -= 0.1 * severity
    
    # ====================================================================
    # SUCCESS-BASED LEARNING
    # ====================================================================
    else:
        
        # Success in irreversible situation → principles mattered
        if situation_features.get("decision_irreversible", 0.0) > 0.5:
            weights.principle_weight += 0.2 * severity
        
        # Success after deliberation + warning usage → warnings worked
        if used["warning"] and situation_features.get("horizon_long", 0.0) > 0.5:
            weights.warning_weight += 0.2 * severity
        
        # Execution success in low-risk scenario → rules gain trust
        if used["rule"] and situation_features.get("risk_high", 0.0) < 0.5:
            weights.rule_weight += 0.2 * severity
    
    # ====================================================================
    # REGRET & RECOVERY SIGNALS
    # ====================================================================
    
    # High regret despite "success" → something was underweighted
    if interpreted_outcome["regret"] > 0.6:
        weights.advice_weight -= 0.2 * severity
        weights.rule_weight -= 0.1 * severity
    
    # Long recovery time → warnings/principles were under-heeded
    if interpreted_outcome["recovery_long"]:
        weights.warning_weight += 0.2 * severity
        weights.principle_weight += 0.1 * severity
    
    # Secondary damage → core knowledge misaligned
    if interpreted_outcome["secondary_damage"]:
        weights.principle_weight -= 0.15 * severity
    
    # ====================================================================
    # FINAL CLAMP (SAFETY CRITICAL)
    # ====================================================================
    # Prevent extreme oscillation. Wisdom learns slowly.
    
    weights.principle_weight = clamp(weights.principle_weight, 0.7, 1.3)
    weights.rule_weight = clamp(weights.rule_weight, 0.7, 1.3)
    weights.warning_weight = clamp(weights.warning_weight, 0.7, 1.3)
    weights.claim_weight = clamp(weights.claim_weight, 0.7, 1.3)
    weights.advice_weight = clamp(weights.advice_weight, 0.7, 1.3)
    
    return weights


def build_training_row(
    features: Dict[str, float],
    outcome: Dict[str, Any],
    situation_features: Dict[str, float],
    constraint_features: Dict[str, float],
    knowledge_features: Dict[str, float]
) -> Tuple[Dict[str, float], TypeWeights]:
    """
    Assemble a single training row from a decision episode.
    
    Returns:
        (features_dict, label_weights)
    """
    label = generate_type_weights(
        situation_features,
        constraint_features,
        knowledge_features,
        outcome
    )
    
    return features, label


def compute_label_certainty(
    severity: float,
    num_similar_episodes: int = 1
) -> float:
    """
    Estimate confidence in the generated label.
    
    Higher severity + more similar episodes = higher certainty.
    """
    # Severity multiplies
    certainty = severity
    
    # More similar episodes increase certainty (but with diminishing returns)
    certainty *= math.log(1 + num_similar_episodes) / math.log(2)
    
    return clamp(certainty, 0.3, 1.0)


def log_label_decision(
    features: Dict[str, float],
    outcome: Dict[str, Any],
    label: TypeWeights,
    severity: float
) -> Dict[str, Any]:
    """
    Log label generation for transparency and debugging.
    
    Ensures all label decisions are auditable.
    """
    return {
        "timestamp": str(__import__('datetime').datetime.now()),
        "scenario_irreversible": features.get("decision_irreversible", 0.0),
        "scenario_severity": severity,
        "outcome_success": outcome.get("success", False),
        "outcome_regret": outcome.get("regret_score", 0.0),
        "label_generated": label.to_dict(),
    }
