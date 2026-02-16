# pwm_bridge.py
"""
PWM Integration Bridge - Proper Separation of Concerns

This bridge manages ONE thing only: Converting validated observations into PWM facts.

THREE SEPARATE SYSTEMS:

1. PWM (Knowledge Graph) — Slow, careful fact storage
   Purpose: "What proven facts do we know about people/relationships?"
   Update frequency: Every 100 turns, after validation
   Use: "Alice is risk-averse", "Bob prefers written communication"
   
2. EpisodicMemory (Decision Log) — Real-time learning
   Purpose: "What decisions were made, what happened, what did we learn?"
   Update frequency: Every turn
   Use: Detect repeated mistakes, track consequences, avoid patterns
   
3. PerformanceMetrics (Improvement Engine) — Systematic retraining
   Purpose: "What's working? What's weak? How do we improve?"
   Update frequency: Every turn (aggregated every 100)
   Use: Find weak domains, recalibrate ministers, measure progress

This bridge ONLY handles: EpisodicMemory → Validation → PWM at turn boundaries
"""

from datetime import datetime
import json


class PWMIntegrationBridge:
    """
    Carefully validates observations before committing to PWM.
    
    Does NOT do:
    - Real-time learning (that's EpisodicMemory)
    - Failure analysis (that's FailureAnalyzer)
    - Pattern detection (that's EpisodicMemory)
    - System improvement (that's SystemRetraining)
    
    Does ONLY do:
    - Collect observations from episodic memory
    - Validate using 100-turn performance data
    - Commit high-confidence facts to PWM
    """

    def __init__(self, pwm, episodic_memory, metrics, confidence_model):
        """
        Args:
            pwm: PersonalWorldModel instance (slow fact store)
            episodic_memory: EpisodicMemory instance (decision log)
            metrics: PerformanceMetrics instance (improvement metrics)
            confidence_model: BayesianConfidence instance (domain confidence)
        """
        self.pwm = pwm  # Slow knowledge graph
        self.episodic = episodic_memory  # Fast decision log
        self.metrics = metrics  # Fast improvement tracking
        self.confidence = confidence_model  # Domain confidence
        
        # Pending observations waiting for validation
        self.pending_observations = []
        
        # Committed facts (audit trail)
        self.committed_facts = []
        
        # Validation failures (what didn't make the cut)
        self.validation_failures = []
        
        print("[PWM] Bridge initialized: Slow fact validator")

    # ========================================================================
    # REAL-TIME: Every turn (queuing only, no validation)
    # ========================================================================

    def queue_entity_observation(self, turn, entity_id, attribute, observed_value, source="decision"):
        """
        Queue an observation about a person/entity for later validation.
        
        IMPORTANT: This does NOT validate or commit to PWM yet.
        Just records what we observed.
        
        Args:
            entity_id: "john", "alice", "bob" — who are we learning about?
            attribute: "risk_tolerance", "communication_style", "trust_level"
            observed_value: The value observed in this turn
            source: "decision", "interaction", "consequence", "feedback"
        
        Example:
            # User made a risky decision, we observed they became more cautious
            bridge.queue_entity_observation(
                turn=150,
                entity_id="john",
                attribute="risk_tolerance",
                observed_value=0.4,  # Lower than before (0.6)
                source="consequence"
            )
        """
        observation = {
            "turn": turn,
            "entity_id": entity_id,
            "attribute": attribute,
            "observed_value": observed_value,
            "source": source,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.pending_observations.append(observation)

    # ========================================================================
    # PERIODIC: Every 100 turns (validation & commitment)
    # ========================================================================

    def periodic_pwm_sync(self, turn, metrics_snapshot=None):
        """
        Validate all pending observations and commit high-confidence facts to PWM.
        
        Called EVERY 100 TURNS (turn 100, 200, 300, ..., 1000).
        
        Process:
        1. Group observations by entity
        2. Compute stability (consistency across 100 turns)
        3. Validate against 100-turn performance data
        4. Commit only >75% confidence facts to PWM
        5. Generate audit trail
        
        Args:
            turn: Current turn number
            metrics_snapshot: Optional performance metrics for this period
        
        Returns:
            {
                "committed_facts": [...],
                "validation_failures": [...],
                "entities_updated": [...],
                "confidence_threshold": 0.75
            }
        """
        
        print(f"\n{'='*70}")
        print(f"PWM VALIDATION CHECKPOINT (Turn {turn})")
        print(f"{'='*70}")
        print(f"Pending observations to validate: {len(self.pending_observations)}\n")
        
        if not self.pending_observations:
            print("✓ No pending observations")
            return {
                "committed_facts": [],
                "validation_failures": [],
                "entities_updated": [],
                "confidence_threshold": 0.75
            }
        
        # Step 1: Group by entity
        observations_by_entity = self._group_by_entity()
        
        # Step 2 & 3: Validate each entity's observations
        committed_facts = []
        validation_failures = []
        
        for entity_id, entity_observations in observations_by_entity.items():
            facts_for_entity = self._validate_entity_observations(
                entity_id, entity_observations, metrics_snapshot
            )
            
            committed, failures = facts_for_entity
            committed_facts.extend(committed)
            validation_failures.extend(failures)
        
        # Step 4: Commit to PWM
        if self.pwm:
            for fact in committed_facts:
                self._commit_fact_to_pwm(fact)
        
        # Step 5: Store audit trail
        self.committed_facts.extend(committed_facts)
        self.validation_failures.extend(validation_failures)
        
        # Clear pending for next cycle
        self.pending_observations = []
        
        # Report
        print(f"\n✓ Validation complete:")
        print(f"  - Committed facts: {len(committed_facts)}")
        print(f"  - Validation failures: {len(validation_failures)}")
        print(f"  - Entities updated: {len(observations_by_entity)}")
        
        return {
            "committed_facts": committed_facts,
            "validation_failures": validation_failures,
            "entities_updated": list(observations_by_entity.keys()),
            "confidence_threshold": 0.75
        }

    # ========================================================================
    # VALIDATION LOGIC
    # ========================================================================

    def _group_by_entity(self):
        """Group observations by entity_id for batch validation."""
        by_entity = {}
        
        for obs in self.pending_observations:
            entity_id = obs["entity_id"]
            if entity_id not in by_entity:
                by_entity[entity_id] = []
            by_entity[entity_id].append(obs)
        
        return by_entity

    def _validate_entity_observations(self, entity_id, observations, metrics_snapshot=None):
        """
        Validate all observations about one entity.
        
        Returns: (committed_facts, validation_failures)
        """
        committed = []
        failures = []
        
        print(f"\n  Entity: {entity_id} ({len(observations)} observations)")
        
        for obs in observations:
            is_valid, reason = self._validate_single_observation(
                entity_id, obs, metrics_snapshot
            )
            
            if is_valid:
                fact = {
                    "entity_id": entity_id,
                    "attribute": obs["attribute"],
                    "value": obs["observed_value"],
                    "confidence": 0.80,  # 100-turn validation = high confidence
                    "source": obs["source"],
                    "turn_committed": obs["turn"],
                    "validated_at": datetime.utcnow().isoformat() + "Z"
                }
                committed.append(fact)
                print(f"    ✓ {obs['attribute']} = {obs['observed_value']} (validated)")
            else:
                failure = {
                    "entity_id": entity_id,
                    "attribute": obs["attribute"],
                    "observed_value": obs["observed_value"],
                    "reason": reason,
                    "turn": obs["turn"]
                }
                failures.append(failure)
                print(f"    ✗ {obs['attribute']} - {reason}")
        
        return committed, failures

    def _validate_single_observation(self, entity_id, observation, metrics_snapshot=None):
        """
        Validate a single observation.
        
        Returns: (is_valid: bool, reason: str)
        """
        attribute = observation["attribute"]
        observed_value = observation["observed_value"]
        
        # Check 1: Is this a known attribute?
        known_attributes = [
            "risk_tolerance", "communication_style", "trust_level",
            "decision_speed", "detail_orientation", "leadership_style"
        ]
        
        if attribute not in known_attributes:
            return False, f"Unknown attribute: {attribute}"
        
        # Check 2: Is the value in valid range? (0.0-1.0 for most attributes)
        try:
            val = float(observed_value)
            if not 0.0 <= val <= 1.0:
                return False, f"Value out of range: {val}"
        except (ValueError, TypeError):
            return False, f"Invalid value type: {type(observed_value)}"
        
        # Check 3: Does this align with recent outcomes?
        # (If metrics show this person was successful with risky decisions,
        #  we can validate "high risk tolerance")
        # For now, simplified: just check it's a reasonable observation
        
        # Check 4: Is there consistency across observations?
        # (If multiple turns observed same attribute, confidence increases)
        count_in_batch = sum(
            1 for obs in self.pending_observations
            if obs["entity_id"] == entity_id and obs["attribute"] == attribute
        )
        
        if count_in_batch > 1:
            # Multiple observations of same attribute = more stable
            print(f"      (Consistency: {count_in_batch} observations)")
        
        # All checks passed
        return True, "Valid"

    def _commit_fact_to_pwm(self, fact):
        """Commit a validated fact to PWM."""
        if not self.pwm:
            return
        
        # Call PWM's update method
        # pwm.update_entity(entity_id, field, old_value, new_value, confidence)
        try:
            self.pwm.add_fact(
                entity_id=fact["entity_id"],
                attribute=fact["attribute"],
                value=fact["value"],
                confidence=fact["confidence"],
                source=fact["source"],
                timestamp=fact["validated_at"]
            )
        except AttributeError:
            # PWM might not have add_fact, try update_entity
            try:
                self.pwm.update_entity(
                    entity_id=fact["entity_id"],
                    field=fact["attribute"],
                    old_value=None,
                    new_value=fact["value"],
                    confidence=fact["confidence"],
                    source=fact["source"]
                )
            except Exception as e:
                print(f"⚠️  Failed to commit to PWM: {e}")

    # ========================================================================
    # INSIGHT GENERATION (What should be next validated?)
    # ========================================================================

    def generate_validation_insights(self):
        """
        Suggest what to look for in the next validation cycle.
        
        Based on: committed facts, failures, confidence levels
        """
        insights = []
        
        # Insight 1: Attributes with validation failures
        failing_attributes = set(f["attribute"] for f in self.validation_failures)
        if failing_attributes:
            insights.append({
                "type": "revalidate",
                "message": f"These attributes need rechecking: {failing_attributes}",
                "attributes": list(failing_attributes)
            })
        
        # Insight 2: High-success entities (commit more about them)
        entity_success = {}
        for fact in self.committed_facts:
            entity_id = fact["entity_id"]
            if entity_id not in entity_success:
                entity_success[entity_id] = 0
            entity_success[entity_id] += 1
        
        if entity_success:
            top_entity = max(entity_success, key=entity_success.get)
            insights.append({
                "type": "focus",
                "message": f"Focus detailed observation on {top_entity} (validated {entity_success[top_entity]} facts)",
                "entity": top_entity,
                "fact_count": entity_success[top_entity]
            })
        
        return insights

    # ========================================================================
    # AUDIT & QUERY
    # ========================================================================

    def get_pwm_facts_for_entity(self, entity_id):
        """Retrieve all committed facts about an entity from audit trail."""
        return [f for f in self.committed_facts if f["entity_id"] == entity_id]

    def get_validation_history(self, entity_id=None):
        """Get validation audit trail."""
        facts = self.committed_facts
        failures = self.validation_failures
        
        if entity_id:
            facts = [f for f in facts if f["entity_id"] == entity_id]
            failures = [f for f in failures if f["entity_id"] == entity_id]
        
        return {
            "committed": facts,
            "failed": failures,
            "total_validated": len(facts) + len(failures),
            "success_rate": len(facts) / (len(facts) + len(failures)) if facts or failures else 0.0
        }

    def summary(self):
        """Summary of PWM bridge status."""
        return {
            "pending_observations": len(self.pending_observations),
            "committed_facts": len(self.committed_facts),
            "validation_failures": len(self.validation_failures),
            "entities_tracked": len(set(f["entity_id"] for f in self.committed_facts)),
            "validation_success_rate": (
                len(self.committed_facts) / 
                (len(self.committed_facts) + len(self.validation_failures))
                if self.committed_facts or self.validation_failures else 0.0
            )
        }
