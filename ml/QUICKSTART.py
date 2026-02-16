"""
Quick Start Guide - ML Wisdom System

This guide shows you how to get the ML system working in 10 minutes.

Example: Decide whether to quit a job
"""

import sys
import os

# Add ML module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ml.kis.knowledge_integration_system import KnowledgeIntegrationSystem, KISRequest
from ml.features.feature_extractor import (
    build_feature_vector,
    SituationState,
    ConstraintState,
    KISOutput,
)
from ml.labels.label_generator import generate_type_weights
from ml.judgment.ml_judgment_prior import MLJudgmentPrior
from ml.ml_orchestrator import MLWisdomOrchestrator


# ============================================================================
# EXAMPLE 1: Basic KIS Synthesis
# ============================================================================

def example_1_basic_kis():
    """Example 1: Use KIS to get relevant knowledge."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic KIS Synthesis")
    print("="*70)
    
    # Initialize KIS
    kis = KnowledgeIntegrationSystem(base_path="data/ministers")
    
    # Create request
    request = KISRequest(
        user_input="Should I quit my job? I'm very unhappy but I don't have savings.",
        active_domains=["career_risk", "optionality_guide", "personal_finance"],
        domain_confidence={
            "career_risk": 0.9,
            "optionality_guide": 0.8,
            "personal_finance": 0.7,
        },
        max_items=5
    )
    
    # Synthesize knowledge
    result = kis.synthesize_knowledge(request)
    
    # Print results
    print("\n[OK] Knowledge Synthesized:")
    print(f"     Items returned: {len(result.synthesized_knowledge)}")
    print(f"     Average KIS: {result.knowledge_quality['avg_kis']:.3f}")
    
    print("\nTop Knowledge Items:")
    for i, knowledge in enumerate(result.synthesized_knowledge, 1):
        print(f"  {i}. {knowledge[:80]}...")
    
    print("\nKnowledge Trace (with attribution):")
    for entry in result.knowledge_trace:
        print(f"  - Domain: {entry['domain'].ljust(20)} Type: {entry['type'].ljust(10)} KIS: {entry['kis']:.3f}")
    
    return result


# ============================================================================
# EXAMPLE 2: Feature Extraction & Label Generation
# ============================================================================

def example_2_features_and_labels():
    """Example 2: Extract features and generate training labels."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Feature Extraction & Label Generation")
    print("="*70)
    
    # Create situation
    situation = SituationState(
        decision_type="irreversible",
        risk_level="high",
        time_horizon="short",
        time_pressure=0.8,
        information_completeness=0.3,
        agency="individual",
        user_input="Should I quit my job?"
    )
    
    # Create constraints (what could break?)
    constraints = ConstraintState(
        irreversibility_score=0.9,
        fragility_score=0.8,
        optionality_loss_score=0.85,
        downside_asymmetry=0.9,
        upside_asymmetry=0.3,
        recovery_time_long=True
    )
    
    # Create mock KIS output
    kis_output = KISOutput(
        knowledge_trace=[
            {"type": "principle", "kis": 0.95},
            {"type": "warning", "kis": 0.92},
            {"type": "rule", "kis": 0.70},
        ],
        used_principle=True,
        used_rule=True,
        used_warning=True,
        used_claim=False,
        used_advice=False,
        avg_kis_principle=0.95,
        avg_kis_rule=0.70,
        avg_kis_warning=0.92,
        avg_kis_claim=0.0,
        avg_kis_advice=0.0,
        num_entries_used=3,
        avg_entry_age_days=60,
        avg_penalty_count=0.1,
    )
    
    # Extract features
    situation_feats = __import__('ml.features.feature_extractor', fromlist=['extract_situation_features']).extract_situation_features(situation)
    constraint_feats = __import__('ml.features.feature_extractor', fromlist=['extract_constraint_features']).extract_constraint_features(constraints)
    kis_feats = __import__('ml.features.feature_extractor', fromlist=['extract_knowledge_features']).extract_knowledge_features(kis_output)
    
    features = {**situation_feats, **constraint_feats, **kis_feats}
    
    print(f"\n[OK] Extracted {len(features)} features")
    print(f"     Situation features: 14")
    print(f"     Constraint features: 6")
    print(f"     Knowledge features: 14")
    
    # Now suppose we made this decision and it failed
    outcome = {
        "success": False,
        "regret_score": 0.8,
        "recovery_time_days": 180,
        "secondary_damage": False,
    }
    
    # Generate training label
    label = generate_type_weights(
        situation_feats,
        constraint_feats,
        kis_feats,
        outcome
    )
    
    print("\n[OK] Generated Training Label (outcome: FAILURE):")
    print(f"     principle_weight:  {label.principle_weight:.3f}  (↑ boosted - failure in irreversible)")
    print(f"     warning_weight:    {label.warning_weight:.3f}  (↑ boosted - long recovery)")
    print(f"     rule_weight:       {label.rule_weight:.3f}  (↓ penalized - rules failed here)")
    print(f"     claim_weight:      {label.claim_weight:.3f}  (→ neutral)")
    print(f"     advice_weight:     {label.advice_weight:.3f}  (→ neutral)")
    
    return features, label


# ============================================================================
# EXAMPLE 3: ML Learning & Inference
# ============================================================================

def example_3_ml_learning():
    """Example 3: Train ML model and get judgement priors."""
    print("\n" + "="*70)
    print("EXAMPLE 3: ML Learning & Inference")
    print("="*70)
    
    # Create ML model
    ml = MLJudgmentPrior(model_path="ml/models")
    
    # Add 10 training samples (simulating past decisions)
    print("\n[...] Adding 10 training samples of past decisions...")
    
    for i in range(10):
        # Simulate: irreversible decisions that failed
        features = {
            "decision_irreversible": 1.0,
            "risk_high": 1.0,
            "irreversibility_score": 0.9,
            # ... 38 other features
        }
        
        label = {
            "principle_weight": 1.3,
            "warning_weight": 1.4,
            "rule_weight": 0.8,
            "claim_weight": 0.9,
            "advice_weight": 0.7,
        }
        
        ml.add_training_sample(features, label)
    
    # Train
    ml.train(force=True)
    print("[OK] Model trained on 10 samples")
    
    # Now make a new decision
    new_features = {
        "decision_irreversible": 1.0,
        "risk_high": 1.0,
        "irreversibility_score": 0.9,
    }
    
    # Get learned priors
    prior, confidence = ml.predict_prior(new_features)
    
    print(f"\n[OK] ML Priors for similar situation (confidence: {confidence:.2%}):")
    print(f"     principle:  {prior['principle_weight']:.2f}  (learned: warnings matter here)")
    print(f"     warning:    {prior['warning_weight']:.2f}  (learned: protect against failure)")
    print(f"     rule:       {prior['rule_weight']:.2f}  (learned: rules less reliable)")
    print(f"     claim:      {prior['claim_weight']:.2f}")
    print(f"     advice:     {prior['advice_weight']:.2f}")
    
    # Save model
    ml.save("ml/models/judgment_prior.json")
    print("\n[OK] Model saved to ml/models/judgment_prior.json")
    
    return ml


# ============================================================================
# EXAMPLE 4: Full Orchestrator Pipeline
# ============================================================================

def example_4_orchestrator():
    """Example 4: Use full orchestrator (currently LLM-optional)."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Full Orchestrator Pipeline")
    print("="*70)
    
    # Initialize components
    kis = KnowledgeIntegrationSystem(base_path="data/ministers")
    ml = MLJudgmentPrior(model_path="ml/models")
    
    # Note: LLM interface requires actual API setup, so we skip it here
    
    # Create orchestrator
    orchestrator = MLWisdomOrchestrator(
        llm_interface=None,  # TODO: wire to actual LLM
        kis_engine=kis,
        ml_prior=ml,
        cache_dir="ml/cache"
    )
    
    # Process a decision
    user_input = "I want to quit my job and start a company. I have 2 months of savings."
    
    print(f"\n[...] Processing decision: '{user_input}'")
    result = orchestrator.process_decision(user_input)
    
    print(f"\n[OK] Decision processed")
    print(f"     Timestamp: {result['timestamp']}")
    print(f"     Pipeline stages completed:")
    
    if "kis" in result["pipeline_stages"]:
        kis_result = result["pipeline_stages"]["kis"]
        print(f"       - KIS: {len(kis_result['synthesized_knowledge'])} items synthesized")
    
    print(f"     Quality metrics: {result['quality']}")
    
    # Later, record outcome
    print(f"\n[...] Recording outcome (simulated: decision failed after 180 days)")
    orchestrator.record_outcome(
        decision_id=0,
        success=False,
        regret_score=0.7,
        recovery_time_days=180
    )
    
    # Save session
    orchestrator.save_session("ml/cache/session.json")
    print(f"[OK] Session saved to ml/cache/session.json")
    
    return orchestrator


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("ML WISDOM SYSTEM - QUICK START GUIDE")
    print("="*70)
    print("\nThis demonstrates the ML Wisdom System on a decision scenario:")
    print("Should I quit my job to start a company?")
    
    try:
        # Example 1: KIS
        kis_result = example_1_basic_kis()
        
        # Example 2: Features & Labels
        features, label = example_2_features_and_labels()
        
        # Example 3: ML Learning
        ml = example_3_ml_learning()
        
        # Example 4: Orchestrator
        orch = example_4_orchestrator()
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*70)
    print("SUCCESS: All examples completed")
    print("="*70)
    print("\nNext steps:")
    print("1. Wire LLMInterface to actual LLM (Claude, Ollama, etc.)")
    print("2. Load real knowledge base from data/ministers/")
    print("3. Run system on real decisions")
    print("4. Collect outcomes to train ML judgment priors")
    print("5. Monitor wisdom metrics in decision logs")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
