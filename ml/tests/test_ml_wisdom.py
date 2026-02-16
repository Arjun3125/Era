"""
ML Wisdom System Tests

Validates all components:
- Feature extraction (correctness, bounds)
- Label generation (learning signals)
- KIS scoring (multi-factor ranking)
- ML judgment priors (learning behavior)
- Integration (end-to-end)
"""

import unittest
import json
import tempfile
import os
from typing import Dict, Any

# Import test modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from features.feature_extractor import (
    extract_situation_features,
    extract_constraint_features,
    extract_knowledge_features,
    extract_action_features,
    build_feature_vector,
    SituationState,
    ConstraintState,
    KISOutput,
    ActionState,
    clamp,
)

from labels.label_generator import (
    generate_type_weights,
    assess_severity,
    interpret_outcome,
    TypeWeights,
)

from kis.knowledge_integration_system import (
    KnowledgeIntegrationSystem,
    KISRequest,
    compute_domain_weight,
    compute_type_weight,
    compute_memory_weight,
    compute_context_weight,
    compute_goal_weight,
)

from judgment.ml_judgment_prior import (
    MLJudgmentPrior,
)


# ============================================================================
# FEATURE EXTRACTION TESTS
# ============================================================================

class TestFeatureExtraction(unittest.TestCase):
    """Test feature extraction correctness and bounds."""
    
    def test_extract_situation_features(self):
        """Test situation feature extraction."""
        situation = SituationState(
            decision_type="irreversible",
            risk_level="high",
            time_horizon="short",
            time_pressure=0.8,
            information_completeness=0.4,
            agency="individual",
            user_input="test"
        )
        
        features = extract_situation_features(situation)
        
        # Check one-hot encoding
        self.assertEqual(features["decision_irreversible"], 1.0)
        self.assertEqual(features["decision_reversible"], 0.0)
        self.assertEqual(features["risk_high"], 1.0)
        
        # Check scalar bounds
        self.assertGreaterEqual(features["time_pressure"], 0.0)
        self.assertLessEqual(features["time_pressure"], 1.0)
    
    def test_extract_constraint_features(self):
        """Test constraint feature extraction."""
        constraints = ConstraintState(
            irreversibility_score=0.9,
            fragility_score=0.7,
            optionality_loss_score=0.8,
            downside_asymmetry=0.85,
            upside_asymmetry=0.3,
            recovery_time_long=True
        )
        
        features = extract_constraint_features(constraints)
        
        # All should be bounded [0,1]
        for v in features.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)
    
    def test_build_feature_vector_bounds(self):
        """Test that complete feature vector is bounded."""
        situation = SituationState(
            decision_type="irreversible",
            risk_level="high",
            time_horizon="short",
            time_pressure=0.8,
            information_completeness=0.4,
            agency="individual",
            user_input="test"
        )
        
        constraints = ConstraintState(
            irreversibility_score=0.9,
            fragility_score=0.7,
            optionality_loss_score=0.8,
            downside_asymmetry=0.85,
            upside_asymmetry=0.3,
            recovery_time_long=True
        )
        
        kis_output = KISOutput(
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
        
        features = build_feature_vector(situation, constraints, kis_output)
        
        # All numeric features should be valid
        for k, v in features.items():
            self.assertIsInstance(v, float)
            # Most should be bounded
            if not k.startswith("num_"):
                self.assertGreaterEqual(v, 0.0, f"{k} below 0")


# ============================================================================
# LABEL GENERATION TESTS
# ============================================================================

class TestLabelGeneration(unittest.TestCase):
    """Test label generation logic."""
    
    def test_severe_failure_boosts_warnings(self):
        """
        TEST 1: Wrong-but-Frequent Knowledge (Anti-Dogma)
        
        Failure in irreversible situation should ↑ warning_weight.
        """
        situation = {"decision_irreversible": 1.0, "risk_high": 1.0}
        constraints = {"irreversibility_score": 0.9, "downside_asymmetry": 0.8}
        knowledge = {"used_warning": 0.0}  # Wasn't using warnings
        outcome = {"success": False, "regret_score": 0.8}
        
        label = generate_type_weights(situation, constraints, knowledge, outcome)
        
        # Warning weight should be boosted
        self.assertGreater(label.warning_weight, 1.0)
    
    def test_execution_success_boosts_rules(self):
        """
        TEST 2: Execution success in low-risk scenario should ↑ rule_weight.
        """
        situation = {"decision_reversible": 1.0, "risk_low": 1.0}
        constraints = {"irreversibility_score": 0.1}
        knowledge = {"used_rule": 1.0}
        outcome = {"success": True, "regret_score": 0.1}
        
        label = generate_type_weights(situation, constraints, knowledge, outcome)
        
        # Rules should get some boost
        self.assertGreater(label.rule_weight, 1.0)
    
    def test_advice_led_failure_penalizes_advice(self):
        """
        TEST 3: Advice-led failures should ↓ advice_weight.
        """
        situation = {}
        constraints = {}
        knowledge = {"used_advice": 1.0}
        outcome = {"success": False, "regret_score": 0.9}
        
        label = generate_type_weights(situation, constraints, knowledge, outcome)
        
        # Advice weight should be penalized
        self.assertLess(label.advice_weight, 1.0)
    
    def test_weights_stay_bounded(self):
        """All generated weights must be bounded [0.7, 1.3]."""
        
        # Test extreme failure
        situation = {"decision_irreversible": 1.0, "risk_high": 1.0, "time_pressure": 1.0}
        constraints = {
            "irreversibility_score": 1.0,
            "downside_asymmetry": 1.0,
            "fragility_score": 1.0
        }
        knowledge = {"used_advice": 1.0, "used_rule": 1.0}
        outcome = {"success": False, "regret_score": 1.0, "recovery_time_days": 500}
        
        label = generate_type_weights(situation, constraints, knowledge, outcome)
        
        # All weights must be bounded
        for weight in [label.principle_weight, label.rule_weight, label.warning_weight,
                       label.claim_weight, label.advice_weight]:
            self.assertGreaterEqual(weight, 0.7, f"Weight {weight} below 0.7")
            self.assertLessEqual(weight, 1.3, f"Weight {weight} above 1.3")


# ============================================================================
# KIS WEIGHT FUNCTION TESTS
# ============================================================================

class TestKISWeights(unittest.TestCase):
    """Test individual KIS weight factors."""
    
    def test_domain_weight_active(self):
        """Domain in active list gets confidence boost."""
        dw = compute_domain_weight(
            "optionality",
            ["optionality", "career_risk"],
            {"optionality": 0.8, "career_risk": 0.6}
        )
        
        self.assertEqual(dw, 0.8)
    
    def test_domain_weight_inactive(self):
        """Domain not in active list gets penalty."""
        dw = compute_domain_weight(
            "philosophy",
            ["optionality"],
            {"optionality": 0.8}
        )
        
        self.assertEqual(dw, 0.25)
    
    def test_type_weight_ranges(self):
        """Type weights match specification."""
        self.assertEqual(compute_type_weight("principle"), 1.0)
        self.assertEqual(compute_type_weight("rule"), 1.1)
        self.assertGreater(compute_type_weight("warning"), 1.0)
        self.assertLess(compute_type_weight("advice"), 1.0)
    
    def test_memory_weight_logarithmic(self):
        """Memory weight scales logarithmically."""
        mw_0 = compute_memory_weight(0)
        mw_1 = compute_memory_weight(1)
        mw_100 = compute_memory_weight(100)
        
        # Should be monotonically increasing
        self.assertLess(mw_0, mw_1)
        self.assertLess(mw_1, mw_100)
        
        # With penalty, should decrease
        mw_100_penalty = compute_memory_weight(100, 3)
        self.assertLess(mw_100_penalty, mw_100)
    
    def test_context_weight_keyword_matching(self):
        """Context weight based on keyword overlap."""
        # 2+ matches
        cw = compute_context_weight(
            "irreversibility and optionality",
            "How do I handle irreversibility and optionality in my career?"
        )
        self.assertEqual(cw, 1.4)


# ============================================================================
# ML JUDGMENT PRIOR TESTS
# ============================================================================

class TestMLJudgmentPrior(unittest.TestCase):
    """Test ML learning behavior."""
    
    def setUp(self):
        """Create fresh ML model."""
        self.ml = MLJudgmentPrior()
    
    def test_neutral_before_training(self):
        """Untrained model returns neutral priors."""
        features = {"decision_irreversible": 1.0, "risk_high": 1.0}
        prior, confidence = self.ml.predict_prior(features)
        
        self.assertEqual(prior["principle_weight"], 1.0)
        self.assertLess(confidence, 0.5)
    
    def test_learning_from_successes(self):
        """Model learns from successful outcomes."""
        
        # Add training samples
        for i in range(10):
            features = {
                "decision_irreversible": 1.0,
                "risk_high": 1.0,
                "irreversibility_score": 0.9
            }
            label = {
                "principle_weight": 1.2,
                "warning_weight": 1.3,
                "rule_weight": 0.8,
                "claim_weight": 1.0,
                "advice_weight": 0.9,
            }
            self.ml.add_training_sample(features, label)
        
        # Train
        self.ml.train(force=True)
        
        # Now should predict boosted weights for similar situation
        features = {"decision_irreversible": 1.0, "risk_high": 1.0, "irreversibility_score": 0.9}
        prior, confidence = self.ml.predict_prior(features)
        
        # Should learn to boost warnings and principles
        self.assertGreater(prior["warning_weight"], 1.0)
        self.assertGreater(prior["principle_weight"], 1.0)
        self.assertGreater(confidence, 0.5)
    
    def test_model_persistence(self):
        """Model can be saved and loaded."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.json")
            
            # Add some data
            self.ml.add_training_sample(
                {"decision_irreversible": 1.0},
                {"principle_weight": 1.3, "rule_weight": 0.8}
            )
            self.ml.train(force=True)
            
            # Save
            self.ml.save(path)
            
            # Load into new model
            ml2 = MLJudgmentPrior()
            success = ml2.load(path)
            
            self.assertTrue(success)
            self.assertEqual(len(ml2.learned_priors), len(self.ml.learned_priors))


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEnd(unittest.TestCase):
    """End-to-end system tests."""
    
    def test_kis_synthesis_nonempty(self):
        """KIS returns non-empty result."""
        kis = KnowledgeIntegrationSystem()
        
        request = KISRequest(
            user_input="Should I quit my job?",
            active_domains=["career_risk", "optionality_guide"],
            domain_confidence={"career_risk": 0.8, "optionality_guide": 0.7},
            max_items=5
        )
        
        result = kis.synthesize_knowledge(request)
        
        # Should return non-empty
        self.assertGreater(len(result.synthesized_knowledge), 0)
        self.assertGreater(len(result.knowledge_trace), 0)
    
    def test_kis_respects_max_items(self):
        """KIS returns at most max_items."""
        kis = KnowledgeIntegrationSystem()
        
        request = KISRequest(
            user_input="test",
            active_domains=["career_risk"],
            domain_confidence={"career_risk": 0.8},
            max_items=3
        )
        
        result = kis.synthesize_knowledge(request)
        
        self.assertLessEqual(len(result.synthesized_knowledge), 3)
        self.assertLessEqual(len(result.knowledge_trace), 3)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    unittest.main()
