"""
Feature Extraction for ML Judgment Learning

Extracts structured feature vectors from decision situations, knowledge usage,
and actions for ML training and inference.

Feature Contract: All values are numeric, bounded, deterministic.
No text embedding. No floating variables.
"""

import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class DecisionType(Enum):
    IRREVERSIBLE = "irreversible"
    REVERSIBLE = "reversible"
    EXPLORATORY = "exploratory"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeHorizon(Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Agency(Enum):
    INDIVIDUAL = "individual"
    ORG = "org"


class ActionType(Enum):
    COMMIT = "commit"
    DELAY = "delay"
    EXPLORE = "explore"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class SituationState:
    """Complete decision situation context."""
    decision_type: str  # "irreversible", "reversible", "exploratory"
    risk_level: str  # "low", "medium", "high"
    time_horizon: str  # "short", "medium", "long"
    time_pressure: float  # 0.0–1.0
    information_completeness: float  # 0.0–1.0
    agency: str  # "individual", "org"
    user_input: str


@dataclass
class ConstraintState:
    """Extracted constraint signals (failures, risks, etc)."""
    irreversibility_score: float  # 0.0–1.0
    fragility_score: float  # 0.0–1.0
    optionality_loss_score: float  # 0.0–1.0
    downside_asymmetry: float  # 0.0–1.0
    upside_asymmetry: float  # 0.0–1.0
    recovery_time_long: bool  # True if recovery_time_days > 90


@dataclass
class KISOutput:
    """Summarized KIS knowledge usage."""
    knowledge_trace: List[Dict[str, Any]]  # All selected entries with metadata
    
    # Aggregated:
    used_principle: bool
    used_rule: bool
    used_warning: bool
    used_claim: bool
    used_advice: bool
    
    # Average KIS per type
    avg_kis_principle: float
    avg_kis_rule: float
    avg_kis_warning: float
    avg_kis_claim: float
    avg_kis_advice: float
    
    # Meta
    num_entries_used: int
    avg_entry_age_days: float
    avg_penalty_count: float


@dataclass
class ActionState:
    """Taken or proposed action."""
    action: str  # "commit", "delay", "explore"
    reversibility: str  # "low", "medium", "high"
    resource_cost: float  # 0.0–1.0


@dataclass
class OutcomeState:
    """Decision outcome for learning."""
    success: bool
    regret_score: float  # 0.0–1.0
    recovery_time_days: int
    secondary_damage: bool


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp x to [lo, hi]."""
    return max(lo, min(hi, x))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default."""
    return numerator / denominator if denominator > 0 else default


# ============================================================================
# FEATURE EXTRACTION FUNCTIONS
# ============================================================================

def extract_situation_features(situation: SituationState) -> Dict[str, float]:
    """
    Extract situation classification features.
    
    Answers: "What kind of decision is this?"
    
    Returns one-hot encoded decision types/risk levels/horizons + scalar measures.
    """
    return {
        # Decision type (one-hot)
        "decision_irreversible": float(situation.decision_type == "irreversible"),
        "decision_reversible": float(situation.decision_type == "reversible"),
        "decision_exploratory": float(situation.decision_type == "exploratory"),
        
        # Risk level (one-hot)
        "risk_low": float(situation.risk_level == "low"),
        "risk_medium": float(situation.risk_level == "medium"),
        "risk_high": float(situation.risk_level == "high"),
        
        # Time horizon (one-hot)
        "horizon_short": float(situation.time_horizon == "short"),
        "horizon_medium": float(situation.time_horizon == "medium"),
        "horizon_long": float(situation.time_horizon == "long"),
        
        # Scalars (0–1)
        "time_pressure": clamp(situation.time_pressure, 0.0, 1.0),
        "information_completeness": clamp(situation.information_completeness, 0.0, 1.0),
        
        # Agency
        "agency_individual": float(situation.agency == "individual"),
        "agency_org": float(situation.agency == "org"),
    }


def extract_constraint_features(constraints: ConstraintState) -> Dict[str, float]:
    """
    Extract constraint signals.
    
    Answers: "What could break if this goes wrong?"
    
    Returns bounded constraint scores. This is the heart of judgment learning.
    """
    return {
        "irreversibility_score": clamp(constraints.irreversibility_score, 0.0, 1.0),
        "fragility_score": clamp(constraints.fragility_score, 0.0, 1.0),
        "optionality_loss_score": clamp(constraints.optionality_loss_score, 0.0, 1.0),
        
        # Asymmetry
        "downside_asymmetry": clamp(constraints.downside_asymmetry, 0.0, 1.0),
        "upside_asymmetry": clamp(constraints.upside_asymmetry, 0.0, 1.0),
        
        # Recovery
        "recovery_time_long": float(constraints.recovery_time_long),
    }


def extract_knowledge_features(kis_output: KISOutput) -> Dict[str, float]:
    """
    Extract knowledge usage summary from KIS output.
    
    Answers: "What kind of knowledge did we rely on?"
    
    Aggregates type usage, KIS scores, and metadata.
    """
    return {
        # Binary usage flags
        "used_principle": float(kis_output.used_principle),
        "used_rule": float(kis_output.used_rule),
        "used_warning": float(kis_output.used_warning),
        "used_claim": float(kis_output.used_claim),
        "used_advice": float(kis_output.used_advice),
        
        # Average KIS per type (non-zero only if type used)
        "avg_kis_principle": clamp(kis_output.avg_kis_principle, 0.0, 10.0),
        "avg_kis_rule": clamp(kis_output.avg_kis_rule, 0.0, 10.0),
        "avg_kis_warning": clamp(kis_output.avg_kis_warning, 0.0, 10.0),
        "avg_kis_claim": clamp(kis_output.avg_kis_claim, 0.0, 10.0),
        "avg_kis_advice": clamp(kis_output.avg_kis_advice, 0.0, 10.0),
        
        # Meta
        "num_entries_used": float(kis_output.num_entries_used),
        "avg_entry_age_days": clamp(kis_output.avg_entry_age_days, 0.0, 1000.0),
        "avg_penalty_count": clamp(kis_output.avg_penalty_count, 0.0, 10.0),
    }


def extract_action_features(action: Optional[ActionState]) -> Dict[str, float]:
    """
    Extract action features.
    
    Answers: "What did we actually do?"
    """
    if action is None:
        return {
            "action_commit": 0.0,
            "action_delay": 0.0,
            "action_explore": 0.0,
            "action_reversibility_low": 0.0,
            "action_reversibility_medium": 0.0,
            "action_reversibility_high": 0.0,
            "action_resource_cost": 0.0,
        }
    
    return {
        "action_commit": float(action.action == "commit"),
        "action_delay": float(action.action == "delay"),
        "action_explore": float(action.action == "explore"),
        
        "action_reversibility_low": float(action.reversibility == "low"),
        "action_reversibility_medium": float(action.reversibility == "medium"),
        "action_reversibility_high": float(action.reversibility == "high"),
        
        "action_resource_cost": clamp(action.resource_cost, 0.0, 1.0),
    }


def build_feature_vector(
    situation: SituationState,
    constraints: ConstraintState,
    kis_output: KISOutput,
    action: Optional[ActionState] = None
) -> Dict[str, float]:
    """
    Assemble complete feature vector for ML.
    
    Single source of truth for feature construction.
    Used for both training and inference.
    """
    features = {}
    
    features.update(extract_situation_features(situation))
    features.update(extract_constraint_features(constraints))
    features.update(extract_knowledge_features(kis_output))
    features.update(extract_action_features(action))
    
    return features


def feature_vector_to_list(feature_dict: Dict[str, float]) -> List[float]:
    """
    Convert feature dict to ordered list (for sklearn, etc).
    
    Maintains consistent ordering across all vectors.
    """
    # Define canonical ordering (alphabetical for determinism)
    keys = sorted(feature_dict.keys())
    return [feature_dict[k] for k in keys]


def get_feature_names() -> List[str]:
    """
    Return canonical feature ordering for ML models.
    """
    # Build a dummy vector to get keys
    dummy_situation = SituationState(
        decision_type="irreversible",
        risk_level="high",
        time_horizon="short",
        time_pressure=0.5,
        information_completeness=0.5,
        agency="individual",
        user_input=""
    )
    dummy_constraints = ConstraintState(
        irreversibility_score=0.5,
        fragility_score=0.5,
        optionality_loss_score=0.5,
        downside_asymmetry=0.5,
        upside_asymmetry=0.5,
        recovery_time_long=False
    )
    dummy_kis = KISOutput(
        knowledge_trace=[],
        used_principle=True,
        used_rule=False,
        used_warning=False,
        used_claim=False,
        used_advice=False,
        avg_kis_principle=0.8,
        avg_kis_rule=0.0,
        avg_kis_warning=0.0,
        avg_kis_claim=0.0,
        avg_kis_advice=0.0,
        num_entries_used=1,
        avg_entry_age_days=30,
        avg_penalty_count=0
    )
    
    features = build_feature_vector(dummy_situation, dummy_constraints, dummy_kis, None)
    return sorted(features.keys())
