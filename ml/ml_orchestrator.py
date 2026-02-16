"""
ML Wisdom System Orchestrator

Integrates all components:
- LLM handshakes (sensing)
- Feature extraction (vectorization)
- KIS (knowledge ranking)
- ML judgment priors (learned bias)
- Label generation (training)
- Outcome recording (feedback loop)

Provides end-to-end pipeline from decision input to wise guidance output
with training data collection for ML improvement.
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from .outcomes.outcome_recorder import OutcomeDatabase, FeedbackIntegrator
from .reward_shaping import reward_function


class MLWisdomOrchestrator:
    """
    Complete ML wisdom pipeline orchestrator.
    
    Pipeline:
    1. User input reception
    2. LLM handshake (situation sensing)
    3. Feature extraction (vectorization)
    4. KIS synthesis (knowledge ranking)
    5. ML judgment bias (learned adjustment)
    6. Diagnosis generation
    7. Output synthesis
    8. Outcome tracking (for learning)
    """
    
    def __init__(
        self,
        llm_interface: Optional[Any] = None,
        kis_engine: Optional[Any] = None,
        ml_prior: Optional[Any] = None,
        cache_dir: str = "ml/cache"
    ):
        self.llm_interface = llm_interface
        self.kis_engine = kis_engine
        self.ml_prior = ml_prior
        self.cache_dir = cache_dir
        
        # Outcome recording and feedback loop (Step 4)
        self.outcome_db = OutcomeDatabase(storage_path=f"{cache_dir}/outcomes")
        self.feedback_integrator = FeedbackIntegrator(
            outcome_db=self.outcome_db,
            ml_prior=ml_prior,
            cache_dir=cache_dir
        )
        
        # Audit trail
        self.decisions_log: List[Dict[str, Any]] = []
        
        os.makedirs(cache_dir, exist_ok=True)
    
    def process_decision(
        self,
        user_input: str,
        require_outcome: bool = False
    ) -> Dict[str, Any]:
        """
        Full decision pipeline.
        
        Returns synthesized guidance with full provenance.
        """
        
        result = {
            "user_input": user_input,
            "timestamp": datetime.now().isoformat(),
            "pipeline_stages": {},
        }
        
        # Stage 1: LLM Handshake (if available)
        if self.llm_interface:
            try:
                llm_output = self.llm_interface.run_handshake_sequence(user_input)
                result["pipeline_stages"]["llm_handshake"] = llm_output
                
                situation_features = self._extract_features_from_llm(llm_output["situation"])
                constraint_features = self._extract_features_from_llm(llm_output["constraints"])
                
            except Exception as e:
                result["errors"] = [f"LLM handshake failed: {str(e)}"]
                situation_features = {}
                constraint_features = {}
        else:
            situation_features = {}
            constraint_features = {}
        
        # Stage 2: KIS Synthesis (if available)
        kis_output = None
        if self.kis_engine and situation_features.get("active_domains"):
            try:
                from features.feature_extractor import KISOutput
                
                kis_result = self.kis_engine.synthesize_knowledge({
                    "user_input": user_input,
                    "active_domains": situation_features.get("active_domains", []),
                    "domain_confidence": situation_features.get("domain_confidence", {}),
                    "max_items": 5,
                })
                
                result["pipeline_stages"]["kis"] = {
                    "synthesized_knowledge": kis_result.synthesized_knowledge,
                    "knowledge_trace": kis_result.knowledge_trace,
                    "knowledge_quality": kis_result.knowledge_quality,
                }
                
                # Convert to feature format
                kis_output = KISOutput(
                    knowledge_trace=kis_result.knowledge_trace,
                    used_principle=any(e["type"] == "principle" for e in kis_result.knowledge_trace),
                    used_rule=any(e["type"] == "rule" for e in kis_result.knowledge_trace),
                    used_warning=any(e["type"] == "warning" for e in kis_result.knowledge_trace),
                    used_claim=any(e["type"] == "claim" for e in kis_result.knowledge_trace),
                    used_advice=any(e["type"] == "advice" for e in kis_result.knowledge_trace),
                    avg_kis_principle=_avg_kis_by_type(kis_result.knowledge_trace, "principle"),
                    avg_kis_rule=_avg_kis_by_type(kis_result.knowledge_trace, "rule"),
                    avg_kis_warning=_avg_kis_by_type(kis_result.knowledge_trace, "warning"),
                    avg_kis_claim=_avg_kis_by_type(kis_result.knowledge_trace, "claim"),
                    avg_kis_advice=_avg_kis_by_type(kis_result.knowledge_trace, "advice"),
                    num_entries_used=len(kis_result.knowledge_trace),
                    avg_entry_age_days=0.0,  # TODO: compute from entries
                    avg_penalty_count=0.0,
                )
                
            except Exception as e:
                result["errors"] = result.get("errors", []) + [f"KIS synthesis failed: {str(e)}"]
                kis_output = None
        
        # Stage 3: Quality Assessment
        quality = self._assess_quality(
            user_input,
            situation_features,
            constraint_features,
            kis_output
        )
        result["quality"] = quality

        # Compute a mode-specific reward when mode is present in the combined input
        # Expected input contains a line: MODE: {MODE_NAME}
        mode = None
        try:
            for line in user_input.splitlines():
                if line.strip().upper().startswith("MODE:"):
                    mode = line.split(":", 1)[1].strip().upper()
                    break
        except Exception:
            mode = None

        if mode:
            try:
                # combine situation features as proxy for features used by reward
                reward = reward_function(mode, situation_features)
                result["reward"] = {"mode": mode, "value": reward}
            except Exception:
                result["reward"] = {"mode": mode, "value": 0.0}
        
        # Stage 4: Build training row (if outcome provided later)
        result["for_training"] = {
            "situation_features": situation_features,
            "constraint_features": constraint_features,
            "kis_features": self._extract_kis_features(kis_output) if kis_output else {},
            "timestamp": result["timestamp"],
        }
        
        # Stage 5: Record decision to outcome database (Step 4)
        decision_key = self.outcome_db.record_decision(
            decision_id=f"decision_{len(self.decisions_log)}",
            user_input=user_input,
            llm_analysis=result["pipeline_stages"].get("llm_handshake", {}),
            kis_guidance=result["pipeline_stages"].get("kis", {}),
            situation_features=situation_features,
            constraint_features=constraint_features,
            knowledge_features=self._extract_kis_features(kis_output) if kis_output else {},
            action=None
        )
        result["decision_key"] = decision_key
        
        # Log for audit
        self.decisions_log.append(result)
        
        return result

    def process_interaction(
        self,
        mode: str,
        user_input: str,
        program_output: str,
        require_outcome: bool = False
    ) -> Dict[str, Any]:
        """
        Adapter for multi-agent simulations.

        Builds a combined input from `mode`, `user_input`, and `program_output`
        and forwards to `process_decision` for feature extraction, KIS,
        and recording. Keeps backward compatibility with `process_decision`.
        """
        combined_input = f"MODE: {mode}\nUSER: {user_input}\nPROGRAM: {program_output}\n"
        return self.process_decision(user_input=combined_input, require_outcome=require_outcome)
    
    def record_outcome(
        self,
        decision_id: int,
        success: bool,
        regret_score: float = 0.0,
        recovery_time_days: int = 0,
        secondary_damage: bool = False,
        notes: str = ""
    ) -> bool:
        """
        Record outcome for a past decision (by index in log).
        
        Enables ML training on historical outcomes.
        Step 4: Persists outcomes to database for training data generation.
        """
        if decision_id < 0 or decision_id >= len(self.decisions_log):
            return False
        
        decision = self.decisions_log[decision_id]
        
        outcome = {
            "success": success,
            "regret_score": regret_score,
            "recovery_time_days": recovery_time_days,
            "secondary_damage": secondary_damage,
            "timestamp": datetime.now().isoformat(),
        }
        
        decision["outcome"] = outcome
        
        # Record to outcome database (Step 4)
        decision_key = decision.get("decision_key")
        if decision_key:
            self.outcome_db.record_outcome(
                decision_key,
                success=success,
                regret_score=regret_score,
                recovery_time_days=recovery_time_days,
                secondary_damage=secondary_damage,
                notes=notes
            )
        
        # Add to ML training
        if self.ml_prior:
            from labels.label_generator import generate_type_weights
            
            label = generate_type_weights(
                decision["for_training"]["situation_features"],
                decision["for_training"]["constraint_features"],
                decision["for_training"]["kis_features"],
                outcome
            )
            
            # Build full feature vector
            features = {
                **decision["for_training"]["situation_features"],
                **decision["for_training"]["constraint_features"],
                **decision["for_training"]["kis_features"],
            }
            
            self.ml_prior.add_training_sample(features, label.to_dict())
            
            # Periodic training
            if len(self.ml_prior.training_data) >= 10:
                self.ml_prior.train()
        
        return True
    
    def run_training_cycle(self) -> Dict[str, Any]:
        """
        Run complete training cycle: outcomes → training data → train model.
        
        Step 4: Closes feedback loop by training ML models on decision outcomes.
        """
        return self.feedback_integrator.run_training_cycle()
    
    def save_session(self, path: str = "ml/cache/session.json"):
        """Save entire session state."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.decisions_log, f, indent=2, default=str)
    
    def load_session(self, path: str = "ml/cache/session.json") -> bool:
        """Load session state."""
        if not os.path.exists(path):
            return False
        
        try:
            with open(path, 'r') as f:
                self.decisions_log = json.load(f)
            return True
        except (json.JSONDecodeError, IOError):
            return False
    
    def _extract_features_from_llm(self, llm_output: Dict[str, Any]) -> Dict[str, float]:
        """Convert LLM output to feature dict."""
        features = {}
        
        for key, value in llm_output.items():
            if isinstance(value, (int, float)):
                features[key] = float(value)
            elif isinstance(value, str):
                # One-hot encoding for categorical
                if key == "decision_type":
                    features[f"decision_{value}"] = 1.0
                elif key == "risk_level":
                    features[f"risk_{value}"] = 1.0
                elif key == "time_horizon":
                    features[f"horizon_{value}"] = 1.0
                elif key == "agency":
                    features[f"agency_{value}"] = 1.0
        
        return features
    
    def _extract_kis_features(self, kis_output: Any) -> Dict[str, float]:
        """Convert KIS output to features."""
        if kis_output is None:
            return {}
        
        return {
            "used_principle": float(kis_output.used_principle),
            "used_rule": float(kis_output.used_rule),
            "used_warning": float(kis_output.used_warning),
            "used_claim": float(kis_output.used_claim),
            "used_advice": float(kis_output.used_advice),
            "avg_kis_principle": kis_output.avg_kis_principle,
            "avg_kis_rule": kis_output.avg_kis_rule,
            "avg_kis_warning": kis_output.avg_kis_warning,
            "avg_kis_claim": kis_output.avg_kis_claim,
            "avg_kis_advice": kis_output.avg_kis_advice,
            "num_entries_used": float(kis_output.num_entries_used),
        }
    
    def _assess_quality(self, user_input: str, situation, constraints, kis_output) -> Dict[str, Any]:
        """Assess overall decision quality."""
        quality = {
            "input_length": len(user_input),
            "has_kis_output": kis_output is not None,
            "has_constraints": bool(constraints),
            "num_domains": len(constraints.get("active_domains", [])) if constraints else 0,
        }
        
        if kis_output:
            quality["num_knowledge_items"] = kis_output.num_entries_used
            quality["best_kis_score"] = kis_output.avg_kis_principle or 0.0
        
        return quality


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _avg_kis_by_type(knowledge_trace: List[Dict], ktype: str) -> float:
    """Compute average KIS for entries of given type."""
    matching = [e.get("kis", 0.0) for e in knowledge_trace if e.get("type") == ktype]
    
    if matching:
        return sum(matching) / len(matching)
    return 0.0
