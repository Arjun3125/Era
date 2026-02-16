# sovereign_orchestrator.py
"""
Complete integration of all learning, validation, and feedback systems.
Orchestrates: Memory, Metrics, Feedback, Validation, Retraining, Dashboard, Stress Testing
"""

from persona.learning.episodic_memory import EpisodicMemory
from persona.learning.consequence_engine import ConsequenceEngine
from persona.learning.confidence_model import BayesianConfidence
from persona.learning.performance_metrics import PerformanceMetrics
from persona.learning.outcome_feedback_loop import OutcomeFeedbackLoop
from persona.learning.failure_analysis import FailureAnalysis
from persona.persistence.conversation_arc import ConversationArc
from persona.pwm_integration.pwm_bridge import PWMIntegrationBridge
from persona.validation.mode_validator import ModeValidator
from persona.validation.identity_validator import IdentityValidator
from hse.simulation.synthetic_human_sim import SyntheticHumanSimulation
from hse.simulation.stress_orchestrator import StressScenarioOrchestrator
from hse.simulation.human_persona_adapter import HumanPersonaAdaptation
from ml.system_retraining import SystemRetraining
from analytics.dashboard import PerformanceDashboard


class SovereignOrchestrator:
    """
    Complete integration of all cognitive systems.
    Manages: memory, consequences, confidence, feedback, validation, learning, stress testing.
    """

    def __init__(self, council, kis_engine, persona_doctrine, user_llm, call_model):
        """
        council: CouncilAggregator (DARBAR ministers)
        kis_engine: KnowledgeEngine (KIS)
        persona_doctrine: Doctrine structure
        user_llm: LLM callable for synthetic human
        call_model: LLM callable for Persona
        """
        
        print("[INIT] Initializing Sovereign Orchestrator...")
        
        # Learning systems
        self.memory = EpisodicMemory(storage_path="episodic_store")
        self.consequences = ConsequenceEngine(seed=42)
        self.confidence = BayesianConfidence()
        self.metrics = PerformanceMetrics(storage_path="metrics_store")
        
        # Feedback & retraining
        self.feedback_loop = OutcomeFeedbackLoop(council, kis_engine)
        self.retrainer = SystemRetraining(council, kis_engine, call_model, self.metrics)
        
        # Validation
        self.arc = ConversationArc()
        self.mode_validator = ModeValidator()
        self.identity_validator = IdentityValidator(persona_doctrine)
        self.failure_analyzer = FailureAnalysis(
            council, kis_engine, self.mode_validator, self.arc, self.metrics
        )
        
        # Character simulation
        self.human_sim = None  # Will be initialized with synthetic human
        self.stress_orchestrator = None
        self.adaptation = HumanPersonaAdaptation()
        
        # Dashboard
        self.dashboard = PerformanceDashboard(
            self.metrics, self.mode_validator, self.identity_validator
        )
        
        # PWM Integration (slow validation of facts)
        self.pwm_bridge = PWMIntegrationBridge(
            pwm=None,  # Will be set if PWM is available
            episodic_memory=self.memory,
            metrics=self.metrics,
            confidence_model=self.confidence
        )
        
        # Config
        self.council = council
        self.kis_engine = kis_engine
        self.call_model = call_model
        self.user_llm = user_llm
        
        print("[✓] Orchestrator initialized")

    def initialize_synthetic_human(self, synthetic_human):
        """Attach synthetic human to simulation"""
        self.human_sim = SyntheticHumanSimulation(synthetic_human, self.user_llm)
        self.stress_orchestrator = StressScenarioOrchestrator(
            synthetic_human, None, self.arc
        )
        print(f"[✓] Synthetic human initialized: {synthetic_human.name}")

    def attach_pwm(self, pwm):
        """Attach Personal World Model for validated fact storage"""
        self.pwm_bridge.pwm = pwm
        print("[✓] PWM attached to orchestrator")

    # ================================================================
    # MAIN SIMULATION TURN
    # ================================================================

    def run_turn(self,
                 turn,
                 user_input,
                 persona_response,
                 current_domain,
                 current_mode,
                 minister_votes,
                 knowledge_items_used,
                 doctrine_applied,
                 emotional_distortion_detected=False,
                 crisis_active=False):
        
        """
        Execute one complete simulation turn with all validation, feedback, and learning.
        
        Returns: {
            'next_input': str,
            'outcome': str,
            'metrics': dict,
            'alerts': list,
            'failure_report': dict or None
        }
        """
        
        result = {
            'next_input': None,
            'outcome': None,
            'metrics': {},
            'alerts': [],
            'failure_report': None
        }
        
        # ================================================================
        # PHASE 1: PRE-GENERATION VALIDATION
        # ================================================================
        
        # Check memory constraints
        memory_check = self.memory.enforce_memory_constraint(current_domain, persona_response)
        if not memory_check['allowed']:
            result['alerts'].append(f"🚨 MEMORY CONSTRAINT: {memory_check['reason']}")
            persona_response = self._force_correction_with_acknowledgment(
                current_domain, memory_check
            )
        
        # Validate mode match
        mode_validation = self.mode_validator.validate_response_mode_match(
            persona_response, current_mode
        )
        if mode_validation['score'] < 0.6:
            result['alerts'].append(f"⚠️  MODE MISMATCH: {mode_validation['issues']}")
            persona_response = self._correct_mode_violation(
                persona_response, current_mode, mode_validation
            )
        
        # Check mode drift
        drift = self.mode_validator.detect_mode_drift(current_mode, persona_response)
        if drift['drift']:
            result['alerts'].append(
                f"⚠️  MODE DRIFT: Conflicting mode detected: {drift['conflicting_mode']}"
            )
        
        # Validate identity consistency
        contradictions = self.identity_validator.check_self_contradiction(turn, persona_response)
        if contradictions:
            result['alerts'].append(
                f"❌ IDENTITY CONTRADICTION: Conflicts with turns {contradictions}"
            )
        
        voice_score = self.identity_validator.validate_voice_consistency([persona_response])
        if voice_score < 0.7:
            result['alerts'].append("⚠️  VOICE INCONSISTENCY: Tone weakened")
        
        if not self.identity_validator.enforce_authority_boundaries(persona_response):
            result['alerts'].append("🚨 AUTHORITY BOUNDARY VIOLATION: Overreach detected")
        
        if not self.identity_validator.meta_character_check(persona_response):
            result['alerts'].append("⚠️  CHARACTER WEAKNESS: Weak language detected")
        
        # ================================================================
        # PHASE 2: INITIALIZE ARC (Turn 1 only)
        # ================================================================
        
        if turn == 1:
            self.arc.set_original_problem(turn, current_domain, user_input)
        
        # Record decision in arc
        self.arc.record_decision(
            turn, current_domain, persona_response,
            self.confidence.get_confidence(current_domain)
        )
        
        # ================================================================
        # PHASE 3: REGISTER CONSEQUENCES & STRESS
        # ================================================================
        
        # Register decision consequence
        consequence_record = self.consequences.register_decision(
            turn, current_domain, persona_response,
            self.confidence.get_confidence(current_domain)
        )
        result['alerts'].append(
            f"📋 Consequence registered: severity {consequence_record['severity']:.2f}, "
            f"triggers in {consequence_record['remaining_turns']} turns"
        )
        
        # Run stress scenario if active
        if crisis_active and self.stress_orchestrator:
            self.stress_orchestrator.run_compounding_crisis(turn, crisis_active)
        
        # ================================================================
        # PHASE 4: SIMULATE HUMAN RESPONSE & OUTCOME
        # ================================================================
        
        next_input = None
        outcome = None
        ml_score = 0.5
        regret_score = 0.0
        severity = 0.5
        
        if self.human_sim:
            # Generate human reaction to persona response
            next_input = self.human_sim.run_simulation_turn(persona_response)
            result['next_input'] = next_input
            
            # Measure advice adoption
            adoption = self.adaptation.measure_advice_adoption(persona_response, next_input)
            result['alerts'].append(f"💬 Advice adoption: {adoption:.1%}")
            
            # Detect adversarial challenge
            challenge = self.adaptation.detect_challenge_behavior(next_input)
            if challenge:
                result['alerts'].append("🔥 Human challenge detected")
            
            # Compute outcome (simplified: can integrate with ML)
            outcome = "failure" if ml_score < 0.5 else "success"
            result['outcome'] = outcome
            
            # Apply consequences to human state
            self.human_sim.apply_consequences(current_domain, outcome, severity)
        else:
            # No synthetic human: use predefined outcome
            outcome = "success" if ml_score >= 0.5 else "failure"
            result['outcome'] = outcome
        
        # ================================================================
        # PHASE 5: UPDATE ALL LEARNING SYSTEMS
        # ================================================================
        
        # Update Bayesian confidence
        self.confidence.update(current_domain, outcome)
        
        # Record to metrics
        self.metrics.record_decision(
            turn, current_domain, persona_response,
            self.confidence.get_confidence(current_domain),
            outcome,
            regret_score,
            situation_type="crisis" if crisis_active else "normal"
        )
        
        # Queue metric insights to PWM bridge for validation at next sync
        # (EpisodicMemory handles decision logging; PWM only stores stable facts)
        if self.pwm_bridge:
            quality_score = self.metrics.get_domain_quality_score(current_domain)
            # If domain performing well, queue observation about domain capability
            if quality_score > 0.7:
                self.pwm_bridge.queue_entity_observation(
                    turn=turn,
                    entity_id=current_domain,
                    attribute="performance_capability",
                    observed_value=quality_score,
                    source="metrics"
                )
        
        # Store in episodic memory
        self.memory.store_episode(
            turn, current_domain, persona_response,
            self.confidence.get_confidence(current_domain),
            outcome,
            f"Severity: {severity}"
        )
        
        # Queue episodic outcome to PWM bridge for validation at next sync
        # (EpisodicMemory itself handles the decision log; PWM just validates and stores facts)
        if self.pwm_bridge and outcome == "failure":
            # High-failure episodes warrant observation about entity understanding
            self.pwm_bridge.queue_entity_observation(
                turn=turn,
                entity_id="persona_understanding",
                attribute=f"{current_domain}_weakness",
                observed_value=regret_score,
                source="decision_outcome"
            )
        
        # Record outcome feedback (drives minister retraining & KIS reweighting)
        self.feedback_loop.record_decision_outcome(
            decision_id=turn,
            domain=current_domain,
            recommended_stance=persona_response,
            minister_votes=minister_votes,
            knowledge_items_used=knowledge_items_used,
            doctrine_applied=doctrine_applied,
            actual_outcome=outcome,
            regret_score=regret_score
        )
        
        # ================================================================
        # PHASE 6: FAILURE ANALYSIS (If outcome is failure)
        # ================================================================
        
        if outcome == "failure":
            failure_report = self.failure_analyzer.analyze_failure(
                decision_id=turn,
                domain=current_domain,
                persona_response=persona_response,
                minister_votes=minister_votes,
                knowledge_items_used=knowledge_items_used,
                doctrine_applied=doctrine_applied,
                emotional_distortion_detected=emotional_distortion_detected,
                claimed_mode=current_mode
            )
            result['failure_report'] = failure_report
            result['alerts'].append(
                f"❌ FAILURE ANALYSIS: {failure_report['root_causes']}"
            )
        
        # ================================================================
        # PHASE 7: TIME-DELAYED CONSEQUENCES
        # ================================================================
        
        triggered = self.consequences.tick()
        for event in triggered:
            result['alerts'].append(
                f"⚠️  DELAYED CONSEQUENCE TRIGGERED from turn {event['origin_turn']}: "
                f"{event['domain']} severity {event['severity']:.2f}"
            )
            self.arc.track_decision_consequences(
                event['origin_turn'], turn, event['domain'], event['severity']
            )
            if self.human_sim:
                self.human_sim.human.unresolved.append(
                    f"Impact from decision at turn {event['origin_turn']}"
                )
        
        # ================================================================
        # PHASE 8: UNRESOLVED LOOP DETECTION
        # ================================================================
        
        loops = self.arc.detect_unresolved_loop(threshold=3)
        if loops:
            result['alerts'].append(f"🔄 UNRESOLVED LOOPS: {loops}")
        
        # ================================================================
        # PHASE 9: DASHBOARD METRICS (Every 10 turns)
        # ================================================================
        
        if turn % 10 == 0:
            rolling = self.dashboard.compute_rolling_metrics(window=100)
            result['metrics'] = rolling
        
        # ================================================================
        # PHASE 10: PERIODIC REPORTING (Every 100 turns)
        # ================================================================
        
        if turn % 100 == 0:
            self._generate_report(turn, result)
        
        # ================================================================
        # PHASE 10.5: PWM SYNC (Every 100 turns after validation)
        # ================================================================
        
        # PWM is for slow fact storage, NOT for driving improvement
        # Improvement comes from PerformanceMetrics → SystemRetraining
        # PWM just validates and commits observable facts after 100 turns
        
        if turn % 100 == 0 and self.pwm_bridge and self.pwm_bridge.pwm is not None:
            # Validate and commit observations queued over the last 100 turns
            pwm_updates = self.pwm_bridge.periodic_pwm_sync(turn)
            result['pwm_updates'] = pwm_updates
            result['alerts'].append(
                f"📚 PWM: {len(pwm_updates.get('committed_facts', []))} facts committed "
                f"({len(pwm_updates.get('validation_failures', []))} failed validation)"
            )
            
            # PWM insights are for AUDIT TRAIL and future reference
            # NOT for changing confidence factors (that's PerformanceMetrics' job)
            insights = self.pwm_bridge.generate_validation_insights()
            if insights:
                for insight in insights:
                    result['alerts'].append(f"  - {insight.get('message', '')}")

        
        # ================================================================
        # PHASE 11: RETRAINING CYCLE (Every 200 turns)
        # ================================================================
        
        if turn % 200 == 0:
            result['alerts'].append("🔄 SYSTEM RETRAINING CYCLE")
            
            # Extract success patterns
            patterns = self.retrainer.extract_success_patterns(num_recent_turns=200)
            result['alerts'].append(f"📊 Extracted patterns: {list(patterns.keys())}")
            
            # Retrain ministers
            self.retrainer.update_minister_confidence_formulas(current_domain)
            
            # Evolve doctrine
            self.retrainer.encode_learned_doctrine()
            
            # Rebalance KIS
            self.retrainer.rebalance_kis_weights()
        
        # ================================================================
        # PHASE 12: STRESS MEASUREMENT (If stress active)
        # ================================================================
        
        if self.stress_orchestrator:
            stress_quality = self.stress_orchestrator.measure_stress_response_quality(
                self.metrics
            )
            result['alerts'].append(f"💪 Stress Response Quality: {stress_quality:.2f}")
        
        return result

    # ================================================================
    # HELPER METHODS
    # ================================================================

    def _force_correction_with_acknowledgment(self, domain, memory_check):
        """Generate correction that acknowledges memory constraint"""
        correction_prompt = f"""
You violated memory constraint: {memory_check['reason']}

Conflicting episodes: {memory_check.get('conflicts', [])}

Correct your response by:
1. Acknowledging the constraint
2. Explaining why conditions have changed
3. Producing a non-contradictory stance
"""
        return self.call_model(correction_prompt)

    def _correct_mode_violation(self, response, mode, validation):
        """Generate mode-corrected response"""
        correction_prompt = f"""
Your response violated {mode.upper()} mode constraints:

Issues: {validation['issues']}

Regenerate the response strictly following {mode.upper()} mode rules:
{self.mode_validator.mode_markers[mode.lower()]}
"""
        return self.call_model(correction_prompt)

    def _generate_report(self, turn, result):
        """Generate comprehensive turn report"""
        print(f"\n{'='*70}")
        print(f"TURN {turn} COMPREHENSIVE REPORT")
        print(f"{'='*70}")
        
        # Metrics
        rolling = self.dashboard.compute_rolling_metrics(window=100)
        print(f"\n📊 ROLLING METRICS (last 100 turns):")
        print(f"  Success Rate: {rolling.get('rolling_success_rate', 0):.1%}")
        print(f"  Stability: {rolling.get('stability', {}).get('stability_score', 0):.2f}")
        
        # Confidence by domain
        print(f"\n🎯 DOMAIN CONFIDENCE:")
        for domain, conf in self.confidence.summary().items():
            print(f"  {domain}: {conf:.2f}")
        
        # Weak domains
        weak = self.dashboard.generate_weak_feature_alert()
        if weak:
            print(f"\n⚠️  WEAK DOMAINS:")
            for item in weak:
                print(f"  {item['domain']}: {item['success_rate']:.1%} ({item['tested']} tests)")
        
        # Retraining suggestions
        suggestions = self.dashboard.suggest_retraining_actions()
        if suggestions:
            print(f"\n💡 RETRAINING SUGGESTIONS:")
            for sugg in suggestions:
                print(f"  • {sugg}")
        
        # Mode stability
        mode_stability = self.mode_validator.mode_stability_score(window=100)
        print(f"\n📌 MODE STABILITY: {mode_stability:.2f}")
        
        # Conversation arc
        if self.arc.original_problem:
            print(f"\n📖 CONVERSATION ARC:")
            print(f"  Original problem: {self.arc.original_problem['description']}")
            print(f"  Status: {self.arc.resolution_status}")
            print(f"  Decisions made: {len(self.arc.decisions_made)}")
        
        print(f"\n{'='*70}\n")

    def get_state_snapshot(self):
        """Get current system state"""
        return {
            'confidence': self.confidence.summary(),
            'metrics_count': len(self.metrics.decisions),
            'memory_episodes': len(self.memory.episodes),
            'mode_switches': self.mode_validator.mode_switches,
            'arc_status': self.arc.resolution_status,
        }
