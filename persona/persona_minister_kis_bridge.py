"""
Minister KIS Integration Layer

Wires the ML Wisdom System (KIS) into DARBAR minister decision-making.

Each minister (risk, optionality, sovereignty, etc.) can now:
1. Request domain-specific knowledge synthesis
2. Shape their recommendations with KIS insights
3. Learn from outcomes to improve future decisions

Integration Points:
- Minister.get_stance() now calls kis.synthesize_knowledge()
- Minister state includes kis_context (synthesized guidance)
- Outcome recording hooks for training feedback
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# Add parent paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from ml.kis.knowledge_integration_system import (
    KnowledgeIntegrationSystem, KISRequest, KISResult
)
from ml.features.feature_extractor import (
    SituationState, ConstraintState, build_feature_vector
)
from ml.ml_orchestrator import MLWisdomOrchestrator


logger = logging.getLogger(__name__)


class MinisterKISBridge:
    """
    Bridge between Ministers and KIS knowledge system.
    
    Enables ministers to query knowledge and learn from outcomes.
    """
    
    def __init__(
        self,
        kis_engine: Optional[KnowledgeIntegrationSystem] = None,
        orchestrator: Optional[MLWisdomOrchestrator] = None,
        knowledge_base_path: str = "data/ministers"
    ):
        """
        Initialize the bridge.
        
        Args:
            kis_engine: KIS instance (creates if None)
            orchestrator: ML orchestrator (creates if None)
            knowledge_base_path: Where knowledge JSON files are stored
        """
        self.kis_engine = kis_engine or KnowledgeIntegrationSystem(base_path=knowledge_base_path)
        self.orchestrator = orchestrator or MLWisdomOrchestrator(kis_engine=self.kis_engine)
        self.knowledge_base_path = knowledge_base_path
        
        # Minister → KIS context mapping
        self.minister_kis_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("MinisterKISBridge initialized")
    
    def get_minister_knowledge(
        self,
        minister_name: str,
        user_input: str,
        domain_list: List[str],
        confidence_levels: Dict[str, float],
        max_items: int = 5
    ) -> Dict[str, Any]:
        """
        Get synthesized knowledge for a minister's decision.
        
        Args:
            minister_name: Name of the minister (risk_minister, optionality_minister, etc.)
            user_input: The decision/query context
            domain_list: Active domains for this minister
            confidence_levels: Confidence in each domain {domain: 0.0-1.0}
            max_items: Max knowledge items to return
        
        Returns:
            {
                "synthesized_knowledge": [...],
                "knowledge_trace": [...],
                "kis_context": {...},
                "decision_id": ...,
            }
        """
        
        # Create KIS request
        request = KISRequest(
            user_input=user_input,
            active_domains=domain_list,
            domain_confidence=confidence_levels,
            max_items=max_items
        )
        
        # Synthesize knowledge
        kis_result = self.kis_engine.synthesize_knowledge(request)
        
        # Record in orchestrator for tracking
        decision_result = self.orchestrator.process_decision(user_input)
        decision_id = len(self.orchestrator.decisions_log) - 1
        
        # Cache for this minister
        cache_key = f"{minister_name}_{decision_id}"
        self.minister_kis_cache[cache_key] = {
            "minister": minister_name,
            "decision_id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "kis_result": kis_result,
            "user_input": user_input,
        }
        
        return {
            "synthesized_knowledge": kis_result.synthesized_knowledge,
            "knowledge_trace": kis_result.knowledge_trace,
            "kis_context": {
                "quality": kis_result.knowledge_quality,
                "debug": kis_result.knowledge_debug,
            },
            "decision_id": decision_id,
            "cache_key": cache_key,
        }
    
    def record_minister_decision(
        self,
        cache_key: str,
        minister_stance: str,
        decision_made: str,
        confidence: float
    ) -> bool:
        """
        Record a minister's decision for auditing.
        
        Args:
            cache_key: From get_minister_knowledge() result
            minister_stance: The minister's recommendation
            decision_made: Actual decision/action taken
            confidence: Minister's confidence (0.0-1.0)
        
        Returns:
            True if recorded successfully
        """
        
        if cache_key not in self.minister_kis_cache:
            logger.warning(f"Cache key not found: {cache_key}")
            return False
        
        cached = self.minister_kis_cache[cache_key]
        cached["decision_recorded"] = {
            "stance": minister_stance,
            "decision": decision_made,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(f"Decision recorded: {cached['minister']} - {decision_made}")
        return True
    
    def record_outcome(
        self,
        cache_key: str,
        success: bool,
        regret_score: float = 0.0,
        recovery_time_days: int = 0,
        notes: str = ""
    ) -> bool:
        """
        Record outcome for learning.
        
        Args:
            cache_key: From get_minister_knowledge()
            success: Whether decision succeeded
            regret_score: 0.0-1.0 regret level
            recovery_time_days: Days to recover if failed
            notes: Human notes on the outcome
        
        Returns:
            True if recorded and used for training
        """
        
        if cache_key not in self.minister_kis_cache:
            logger.warning(f"Cache key not found for outcome: {cache_key}")
            return False
        
        cached = self.minister_kis_cache[cache_key]
        decision_id = cached["decision_id"]
        
        # Record in orchestrator
        success = self.orchestrator.record_outcome(
            decision_id=decision_id,
            success=success,
            regret_score=regret_score,
            recovery_time_days=recovery_time_days,
            secondary_damage=False
        )
        
        # Add outcome to cache
        cached["outcome"] = {
            "success": success,
            "regret": regret_score,
            "recovery_days": recovery_time_days,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(f"Outcome recorded: {cached['minister']} - {'SUCCESS' if success else 'FAILURE'}")
        
        # Save session
        self.orchestrator.save_session("ml/cache/minister_session.json")
        
        return True
    
    def get_minister_context(self, minister_name: str) -> Dict[str, Any]:
        """
        Get KIS context for a specific minister.
        
        Useful for rendering minister decision explanations.
        """
        
        contexts = [
            cache for cache in self.minister_kis_cache.values()
            if cache["minister"] == minister_name
        ]
        
        if not contexts:
            return {}
        
        # Return most recent
        return contexts[-1]
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get summary of what the system has learned so far.
        """
        
        num_decisions = len(self.orchestrator.decisions_log)
        num_outcomes = sum(
            1 for d in self.orchestrator.decisions_log
            if "outcome" in d
        )
        
        # Get ML model state
        if self.orchestrator.ml_prior:
            num_learned_situations = len(self.orchestrator.ml_prior.learned_priors)
            num_training_samples = self.orchestrator.ml_prior.state.num_training_samples
        else:
            num_learned_situations = 0
            num_training_samples = 0
        
        return {
            "total_decisions": num_decisions,
            "outcomes_recorded": num_outcomes,
            "learning_rate": num_outcomes / max(num_decisions, 1),
            "situations_learned": num_learned_situations,
            "training_samples": num_training_samples,
            "model_epochs": self.orchestrator.ml_prior.state.training_epochs if self.orchestrator.ml_prior else 0,
        }
    
    def export_minister_logs(self, filepath: str) -> bool:
        """
        Export all minister decision logs to JSON.
        """
        
        try:
            with open(filepath, 'w') as f:
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "minister_cache": self.minister_kis_cache,
                    "learning_summary": self.get_learning_summary(),
                }
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported minister logs to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False


# ============================================================================
# EXAMPLE: How to use in Minister code
# ============================================================================

def minister_usage_example():
    """
    Example: How to integrate KIS into a Minister's get_stance() method.
    
    This is pseudocode showing the integration pattern.
    """
    
    # In risk_minister.py or similar:
    
    """
    from persona_minister_kis_bridge import MinisterKISBridge
    
    class RiskMinister:
        def __init__(self):
            self.kis_bridge = MinisterKISBridge()
        
        def get_stance(self, user_input, state):
            # Get KIS knowledge for risk domain
            kis_result = self.kis_bridge.get_minister_knowledge(
                minister_name="risk_minister",
                user_input=user_input,
                domain_list=["career_risk", "personal_finance"],
                confidence_levels={"career_risk": 0.9, "personal_finance": 0.7},
                max_items=5
            )
            
            # Use synthesized knowledge to shape stance
            synthesized_knowledge = kis_result["synthesized_knowledge"]
            
            # Risk minister's reasoning (now informed by KIS)
            stance = "CAUTION: Wait for financial buffer"
            if any("irreversible" in k for k in synthesized_knowledge):
                stance = "HIGH_RISK: Delay until conditions improve"
            
            self.kis_bridge.record_minister_decision(
                cache_key=kis_result["cache_key"],
                minister_stance=stance,
                decision_made="delay",
                confidence=0.85
            )
            
            return stance
        
        def receive_outcome(self, success, regret, recovery_days):
            # Later, when outcome is known
            self.kis_bridge.record_outcome(
                cache_key=...,  # passed from earlier
                success=success,
                regret_score=regret,
                recovery_time_days=recovery_days
            )
    """
    pass


if __name__ == "__main__":
    # Test the bridge
    print("\n[...] Initializing MinisterKISBridge...")
    bridge = MinisterKISBridge()
    
    print("[OK] Bridge initialized")
    
    # Example query
    kis_result = bridge.get_minister_knowledge(
        minister_name="risk_minister",
        user_input="Should I quit my job without savings?",
        domain_list=["career_risk", "personal_finance"],
        confidence_levels={"career_risk": 0.9, "personal_finance": 0.8},
        max_items=5
    )
    
    print(f"[OK] Got {len(kis_result['synthesized_knowledge'])} knowledge items")
    print(f"     Decision ID: {kis_result['decision_id']}")
    
    # Record decision
    bridge.record_minister_decision(
        cache_key=kis_result["cache_key"],
        minister_stance="CAUTION: Build financial buffer first",
        decision_made="delay_decision",
        confidence=0.85
    )
    print("[OK] Decision recorded")
    
    # Record outcome (simulated)
    bridge.record_outcome(
        cache_key=kis_result["cache_key"],
        success=True,
        regret_score=0.2,
        recovery_time_days=0,
        notes="Waited 3 months, accumulated savings, made better decision"
    )
    print("[OK] Outcome recorded (training data)")
    
    # Get learning summary
    summary = bridge.get_learning_summary()
    print("\n[OK] Learning Summary:")
    for k, v in summary.items():
        print(f"     {k}: {v}")
    
    # Export logs
    bridge.export_minister_logs("ml/cache/minister_kis_logs.json")
    print("[OK] Logs exported to ml/cache/minister_kis_logs.json")
