"""
ML Wisdom System - Complete Integration Guide

Steps 2, 3, and 4 fully implemented and integrated.
Ready for production deployment with continuous learning.
"""

# ==============================================================================
# QUICK START - USING THE COMPLETE ML WISDOM SYSTEM
# ==============================================================================

from ml.ml_orchestrator import MLWisdomOrchestrator
from ml.judgment.ml_judgment_prior import MLJudgmentPrior
from ml.llm_handshakes.llm_interface import LLMInterface
from ml.kis.knowledge_integration_system import KnowledgeIntegrationSystem


# Setup (do once)
# ==============================================================================

def setup_ml_wisdom_system():
    """Initialize complete ML wisdom system."""
    
    # Step 3: LLM client
    llm = LLMInterface(
        model="huihui_ai/deepseek-r1-abliterated:8b",
        base_url="http://localhost:11434",
        max_retries=2,
        timeout=90
    )
    
    # Step 2: KIS engine
    kis = KnowledgeIntegrationSystem()
    
    # Step 4: ML learning
    ml_prior = MLJudgmentPrior()
    
    # Integration
    orchestrator = MLWisdomOrchestrator(
        llm_interface=llm,
        kis_engine=kis,
        ml_prior=ml_prior,
        cache_dir="ml/cache"
    )
    
    return orchestrator


# Usage Pattern 1: Single Decision with Outcome
# ==============================================================================

def make_decision_with_tracking(orchestrator, situation: str):
    """
    Make a decision with full tracking for later learning.
    
    Returns: (decision_result, decision_key_for_tracking)
    """
    
    # Step 1: Make decision (uses LLM + KIS + learned priors)
    result = orchestrator.process_decision(user_input=situation)
    
    decision_key = result["decision_key"]
    
    # Extract guidance
    guidance = {
        "llm_analysis": result["pipeline_stages"].get("llm_handshake"),
        "kis_items": result["pipeline_stages"].get("kis"),
        "quality": result.get("quality"),
        "timestamp": result["timestamp"]
    }
    
    # Return for display/logging
    return guidance, decision_key


def record_decision_outcome(orchestrator, decision_id: int, outcome: dict):
    """
    Record what actually happened for ML training.
    
    outcome: {
        "success": bool,
        "regret_score": float (0-1),
        "recovery_time_days": int,
        "secondary_damage": bool,
        "notes": str (optional)
    }
    """
    
    orchestrator.record_outcome(
        decision_id=decision_id,
        success=outcome["success"],
        regret_score=outcome.get("regret_score", 0.0),
        recovery_time_days=outcome.get("recovery_time_days", 0),
        secondary_damage=outcome.get("secondary_damage", False)
    )


# Usage Pattern 2: Batch Decision Cycles
# ==============================================================================

def run_decision_batch(orchestrator, decisions: list) -> list:
    """
    Make multiple decisions with full tracking.
    
    decisions: [
        {"input": "Decision 1?"},
        {"input": "Decision 2?"},
        ...
    ]
    
    Returns: [decision_key_1, decision_key_2, ...]
    """
    
    decision_keys = []
    
    for decision in decisions:
        result = orchestrator.process_decision(
            user_input=decision["input"]
        )
        decision_keys.append(result["decision_key"])
    
    return decision_keys


def record_batch_outcomes(orchestrator, outcomes: list):
    """
    Record outcomes for batch of decisions.
    
    outcomes: [
        {"decision_id": 0, "success": true, "regret_score": 0.2, ...},
        {"decision_id": 1, "success": false, "regret_score": 0.8, ...},
    ]
    """
    
    for outcome in outcomes:
        orchestrator.record_outcome(
            decision_id=outcome["decision_id"],
            success=outcome.get("success", False),
            regret_score=outcome.get("regret_score", 0.0),
            recovery_time_days=outcome.get("recovery_time_days", 0),
            secondary_damage=outcome.get("secondary_damage", False)
        )


# Usage Pattern 3: Training & Model Updates
# ==============================================================================

def train_on_accumulated_outcomes(orchestrator) -> dict:
    """
    Run training cycle on accumulated outcomes.
    
    Generates training data, trains ML models, saves weights.
    
    Returns: {
        "status": "success|skipped|failed",
        "samples_trained": int,
        "model_file": str,
        "dataset_file": str
    }
    """
    
    return orchestrator.run_training_cycle()


def check_system_status(orchestrator) -> dict:
    """Get status of ML wisdom system."""
    
    stats = orchestrator.outcome_db.get_statistics()
    
    return {
        "decisions_recorded": stats["total_decisions_recorded"],
        "outcomes_recorded": stats["decisions_with_outcomes"],
        "success_rate": stats["success_rate"],
        "training_samples": stats["decisions_with_outcomes"],
        "high_regret_count": stats["high_regret_count"],
        "secondary_damage_count": stats["secondary_damage_count"],
    }


# ==============================================================================
# INTEGRATION POINTS
# ==============================================================================

# With Minister System (decision-making)
# - Ministers call process_decision(situation)
# - Get structured guidance from system
# - Record outcomes via record_outcome()

# With Ingestion System (Step 2)
# - Ingestion Phase 2 enhances doctrines with KIS
# - Doctrine.kis_guidance provides domain knowledge
# - System learns what knowledge matters

# With Orchestrator (Steps 3-4)
# - LLMInterface provides structured analysis (Step 3)
# - OutcomeDatabase records decisions & outcomes (Step 4)
# - MLJudgmentPrior learns from outcomes (Step 4)

# ==============================================================================
# DATA FLOW
# ==============================================================================

"""
Decision Input
    ↓
[Step 3] LLM Handshake (4-call analysis)
  → Situation framing
  → Constraint extraction
  → Counterfactual sketch
  → Intent detection
    ↓
[Step 2] KIS Synthesis (3 relevant items)
  → Multi-factor ranking (5 factors)
  → Top items selected
  → Knowledge_quality scored
    ↓
[Step 4] Record Decision
  → Store features for training
  → Store guidance + analysis
  → Keep decision_key for tracking
    ↓
⚡ Synthesized Guidance to User
    ↓
[Execute Decision in Real World]
    ↓
[Observe Outcome]
    ↓
[Step 4] Record Outcome
  → Store success/regret/recovery
  → Generate training labels
  → If ≥10 samples: auto-train
    ↓
[Step 4] Training Cycle (periodic)
  → Generate training dataset
  → Train ML judgment prior
  → Save model weights
    ↓
[Apply Learned Weights]
  → KIS uses learned priors
  → Next decision improved by learning
    ↓
[Repeat for continuous improvement]
"""

# ==============================================================================
# EXAMPLE: COMPLETE DECISION CYCLE
# ==============================================================================

def complete_decision_cycle_example():
    """End-to-end example of using ML wisdom system."""
    
    # Setup
    orchestrator = setup_ml_wisdom_system()
    
    # Make decision 1
    situation1 = "Should we commit $1M to this startup investment?"
    guidance1, key1 = make_decision_with_tracking(orchestrator, situation1)
    
    print(f"Decision Key: {key1}")
    print(f"LLM Analysis: {guidance1['llm_analysis']}")
    print(f"KIS Items: {guidance1['kis_items']}")
    
    # [Execute decision, observe outcome over 6 months]
    
    # Record outcome for decision 1
    record_decision_outcome(orchestrator, 0, {
        "success": True,
        "regret_score": 0.15,
        "recovery_time_days": 0,
        "secondary_damage": False
    })
    
    # Make decision 2 (same category)
    situation2 = "Should we commit $2M to this other startup?"
    guidance2, key2 = make_decision_with_tracking(orchestrator, situation2)
    
    # Record outcome for decision 2
    record_decision_outcome(orchestrator, 1, {
        "success": False,
        "regret_score": 0.85,
        "recovery_time_days": 90,
        "secondary_damage": True
    })
    
    # Make decision 3
    situation3 = "Should we commit $500K to this venture?"
    guidance3, key3 = make_decision_with_tracking(orchestrator, situation3)
    
    # Record outcome
    record_decision_outcome(orchestrator, 2, {
        "success": True,
        "regret_score": 0.1,
        "recovery_time_days": 0,
        "secondary_damage": False
    })
    
    # [Accumulate more outcomes...]
    
    # When ≥5 outcomes recorded: train
    status = check_system_status(orchestrator)
    print(f"\nSystem Status: {status['outcomes_recorded']} outcomes recorded")
    
    if status["outcomes_recorded"] >= 5:
        training_result = train_on_accumulated_outcomes(orchestrator)
        print(f"Training Result: {training_result}")
        print(f"Learned {training_result['learned_priors_count']} situation priors")


# ==============================================================================
# CONFIGURATION & CUSTOMIZATION
# ==============================================================================

# Customize LLM
# orchestrator.llm_interface = LLMInterface(
#     model="different/model:7b",
#     base_url="http://custom-ollama:11434",
#     max_retries=3,
#     timeout=120
# )

# Customize KIS
# orchestrator.kis_engine = KnowledgeIntegrationSystem(
#     knowledge_source="custom/data/knowledge.json",
#     max_items=5
# )

# Customize ML Training
# orchestrator.feedback_integrator.run_training_cycle()


# ==============================================================================
# MONITORING & ANALYTICS
# ==============================================================================

def get_learning_metrics(orchestrator) -> dict:
    """Get metrics about system learning."""
    
    stats = orchestrator.outcome_db.get_statistics()
    
    metrics = {
        "total_decisions": stats["total_decisions_recorded"],
        "total_outcomes": stats["decisions_with_outcomes"],
        "success_rate": stats["success_rate"],
        "avg_regret": "TBD",  # Could compute from outcomes
        "training_readiness": (
            "Ready to train" 
            if stats["decisions_with_outcomes"] >= 5 
            else f"Need {5 - stats['decisions_with_outcomes']} more outcomes"
        )
    }
    
    return metrics


# ==============================================================================
# TROUBLESHOOTING
# ==============================================================================

def troubleshoot_system(orchestrator):
    """Check system health."""
    
    checks = {
        "outcome_database": "OK" if orchestrator.outcome_db else "MISSING",
        "feedback_integrator": "OK" if orchestrator.feedback_integrator else "MISSING",
        "ml_prior": "OK" if orchestrator.ml_prior else "MISSING",
        "llm_interface": "OK" if orchestrator.llm_interface else "MISSING",
        "kis_engine": "OK" if orchestrator.kis_engine else "MISSING",
        "outcomes_recorded": orchestrator.outcome_db.get_statistics()["total_decisions_recorded"],
    }
    
    return checks


# ==============================================================================
# FILES & STORAGE
# ==============================================================================

"""
Database Files:
  ml/cache/outcomes/
    - outcome_records.jsonl    [Decisions + Outcomes]
    - outcome_index.json       [Fast lookup index]
    - outcome_stats.json       [Statistics cache]

Model Files:
  ml/models/
    - judgment_prior_*.json    [Trained model states]

Training Datasets:
  ml/cache/training_datasets/
    - training_dataset_*.json  [Generated training data]

Logs:
  ml/cache/
    - training_log.jsonl       [Training events]
    - session.json            [Session state]
"""

# ==============================================================================
# DEPLOYMENT CHECKLIST
# ==============================================================================

"""
Before production:
  ☐ Ollama server running: ollama serve
  ☐ Model downloaded: ollama pull huihui_ai/deepseek-r1-abliterated:8b
  ☐ LLM connectivity tested: see test_step3_simple.py
  ☐ KIS system loaded with knowledge items
  ☐ Ingestion pipeline enhanced with KIS (verify 33 doctrines)
  ☐ ML prior initialized and ready to train
  ☐ Data directories created: ml/cache/outcomes, ml/models, etc
  ☐ Test cycle: 5 decisions → outcomes → training → verify

Production monitoring:
  ☐ Track decision success rates
  ☐ Monitor outcome recording (should be 80%+)
  ☐ Watch for training triggers (every 5+ outcomes)
  ☐ Validate learned weights improve decisions
  ☐ Log all decision guidance for audit trail
"""

# ==============================================================================
# FURTHER IMPROVEMENTS
# ==============================================================================

"""
Phase 5: Active Learning
  - Identify uncertain decisions
  - Request outcome feedback proactively
  - Prioritize high-impact outcomes

Phase 6: Advanced Modeling
  - Replace simple prior with neural model
  - Multi-task learning across decision types
  - Transfer learning from similar situations

Phase 7: Explainability
  - Why did system recommend X?
  - Which features triggered which weights?
  - How did learning affect this decision?

Phase 8: Real-World Integration
  - Minister system auto-records outcomes
  - Continuous deployment of improved models
  - A/B testing of learning approaches
  - Performance dashboards
"""

# ==============================================================================

if __name__ == "__main__":
    print("ML Wisdom System - Integration Guide")
    print("====================================")
    print()
    print("This module provides complete usage patterns for:")
    print("  - Making decisions with LLM + KIS + learned priors (Steps 2-3)")
    print("  - Recording outcomes for continuous learning (Step 4)")
    print("  - Training ML models on accumulated data (Step 4)")
    print("  - Monitoring system health and learning progress")
    print()
    print("See setup_ml_wisdom_system() for initialization")
    print("See make_decision_with_tracking() for decision usage")
    print("See record_decision_outcome() for outcome recording")
    print("See train_on_accumulated_outcomes() for training")
