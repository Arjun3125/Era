"""
ML Judgment Prior Layer

Learns from decision outcomes to biases KIS scoring toward knowledge
types that repeatedly succeed in similar situations.

Uses simple, interpretable models (no deep learning).
Stays bounded and sovereign.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import math


@dataclass
class MLModelState:
    """Serializable ML model state."""
    version: str = "1.0"
    num_training_samples: int = 0
    feature_names: List[str] = None
    
    # Simple: store learned type-weight adjustments per situation class
    prior_cache: Dict[str, Dict[str, float]] = None  # situation_hash -> type_weights
    
    training_epochs: int = 0
    last_training_timestamp: str = ""


class MLJudgmentPrior:
    """
    ML layer that learns judgment biases from outcomes.
    
    Does NOT:
    - Make decisions
    - Override rules
    - Replace KIS
    
    Does:
    - Adjust type weights based on historical patterns
    - Learn which knowledge types succeed in similar situations
    - Stay bounded [0.7, 1.3]
    """
    
    def __init__(self, model_path: str = "ml/models"):
        self.model_path = model_path
        self.state = MLModelState()
        self.feature_names = []
        
        # Training dataset
        self.training_data: List[Tuple[Dict[str, float], Dict[str, float]]] = []
        
        # Simple in-memory learned priors
        self.learned_priors: Dict[str, Dict[str, float]] = {}
        
        # Evaluation mode flag - disables ML prior for ablation studies
        self.disabled = False
        
        os.makedirs(model_path, exist_ok=True)
    
    def compute_situation_hash(self, situation_features: Dict[str, float]) -> str:
        """
        Create a hash key for situation classification.
        
        Maps situation to discretized bucket for prior lookup.
        """
        decision_type = (
            "irreversible" if situation_features.get("decision_irreversible", 0) > 0.5
            else "reversible" if situation_features.get("decision_reversible", 0) > 0.5
            else "exploratory"
        )
        
        risk_level = (
            "high" if situation_features.get("risk_high", 0) > 0.5
            else "medium" if situation_features.get("risk_medium", 0) > 0.5
            else "low"
        )
        
        irreversibility = "h" if situation_features.get("irreversibility_score", 0.0) > 0.7 else "l"
        
        return f"{decision_type}_{risk_level}_{irreversibility}"
    
    def add_training_sample(
        self,
        features: Dict[str, float],
        label: Dict[str, float]
    ):
        """
        Add a training sample (features -> learned type weights).
        
        Does not immediately train. Accumulates for batch learning.
        """
        self.training_data.append((features, label))
    
    def train(self, force: bool = False) -> bool:
        """
        Train the model from accumulated samples.
        
        Simple algorithm:
        1. Group samples by situation_hash
        2. Average learned weights per group
        3. Store as priors
        
        Returns True if training occurred.
        """
        if len(self.training_data) < 5 and not force:
            # Need minimum data
            return False
        
        # Group by situation hash
        grouped: Dict[str, List[Dict[str, float]]] = {}
        
        for features, label in self.training_data:
            situation_hash = self.compute_situation_hash(features)
            
            if situation_hash not in grouped:
                grouped[situation_hash] = []
            
            grouped[situation_hash].append(label)
        
        # Compute averages per group
        self.learned_priors = {}
        
        for situation_hash, labels in grouped.items():
            avg_weights = {
                "principle_weight": sum(l.get("principle_weight", 1.0) for l in labels) / len(labels),
                "rule_weight": sum(l.get("rule_weight", 1.0) for l in labels) / len(labels),
                "warning_weight": sum(l.get("warning_weight", 1.0) for l in labels) / len(labels),
                "claim_weight": sum(l.get("claim_weight", 1.0) for l in labels) / len(labels),
                "advice_weight": sum(l.get("advice_weight", 1.0) for l in labels) / len(labels),
            }
            
            self.learned_priors[situation_hash] = avg_weights
        
        self.state.num_training_samples = len(self.training_data)
        self.state.training_epochs += 1
        
        return True
    
    def predict_prior(
        self,
        situation_features: Dict[str, float],
        confidence_threshold: float = 0.6
    ) -> Tuple[Dict[str, float], float]:
        """
        Predict ML-learned type weights for a situation.
        
        Returns:
            (prior_weights, confidence)
        
        prior_weights: type -> weight adjustment [0.7, 1.3]
        confidence: how confident the model is in this prediction
        
        (Disabled in evaluation mode - ablation study for ML prior importance)
        """
        
        # Return neutral weights if disabled
        if self.disabled:
            return {
                "principle_weight": 1.0,
                "rule_weight": 1.0,
                "warning_weight": 1.0,
                "claim_weight": 1.0,
                "advice_weight": 1.0,
            }, 0.0
        
        situation_hash = self.compute_situation_hash(situation_features)
        
        # If we have learned prior for this situation
        if situation_hash in self.learned_priors:
            weights = self.learned_priors[situation_hash]
            
            # Confidence based on number of samples for this situation
            num_samples = sum(
                1 for features, _ in self.training_data
                if self.compute_situation_hash(features) == situation_hash
            )
            
            # More samples = higher confidence (logarithmic)
            confidence = min(0.95, 0.5 + 0.1 * math.log(1 + num_samples))
            
            return weights, confidence
        
        # No learned prior - return neutral
        return {
            "principle_weight": 1.0,
            "rule_weight": 1.0,
            "warning_weight": 1.0,
            "claim_weight": 1.0,
            "advice_weight": 1.0,
        }, 0.3
    
    def apply_ml_bias(
        self,
        kis_scores: Dict[str, float],  # type -> KIS score
        situation_features: Dict[str, float],
        ml_confidence_threshold: float = 0.6
    ) -> Dict[str, float]:
        """
        Apply ML-learned biases to KIS scores.
        
        Only applies if confidence high enough.
        
        KIS adjustment:
            adjusted_KIS = KIS × ml_prior_weight
        
        (Disabled in evaluation mode - ablation study for ML prior importance)
        """
        
        # Return unchanged if disabled
        if self.disabled:
            return kis_scores
        
        ml_prior, confidence = self.predict_prior(situation_features, ml_confidence_threshold)
        
        # Only apply if confident
        if confidence < ml_confidence_threshold:
            return kis_scores
        
        adjusted = {}
        for ktype, kis_score in kis_scores.items():
            weight_key = f"{ktype}_weight"
            ml_weight = ml_prior.get(weight_key, 1.0)
            adjusted[ktype] = kis_score * ml_weight
        
        return adjusted
    
    def save(self, path: str = "ml/models/judgment_prior.json"):
        """Persist model state."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        data = {
            "state": asdict(self.state),
            "learned_priors": self.learned_priors,
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path: str = "ml/models/judgment_prior.json") -> bool:
        """Load persisted model state."""
        if not os.path.exists(path):
            return False
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.learned_priors = data.get("learned_priors", {})
                return True
        except (json.JSONDecodeError, IOError):
            return False
    
    def reset(self):
        """Clear all learned state."""
        self.training_data = []
        self.learned_priors = {}
        self.state = MLModelState()
