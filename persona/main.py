# persona/main.py
"""
Main interactive loop with clarifying-question integration.

Key additions:
- Creates a PersonaBrain and uses it to decide when to HALT and ask clarifying questions.
- Calls situation/coherence handshakes synchronously (short) to provide the Brain
  with the info it needs immediately.
- Asks clarifying question via llm.speak() (overrides question suppression for that single utterance).
- Tracks awaiting_clarification and expected_clarification in state.
"""

import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError
from typing import Optional, Dict, Any

from .state import CognitiveState
from .context import build_system_context, trim_response, enforce_frequency, MODE_INERTIA
from .trace import trace, print_trace, DEBUG_OBSERVER
from .analysis import (
    assess_situation,
    assess_situation_heuristic,
    generate_clarifying_questions,
    assess_mode_fitness,
    classify_domains,
    assess_emotional_metrics,
    assess_coherence,
)
from .knowledge_engine import synthesize_knowledge
from .brain import PersonaBrain
from .clarify import build_clarifying_question, format_question_for_user
from .council import CouncilAggregator
from sovereign.prime_confident import PrimeConfident

# NEW: Learning systems
from .learning.episodic_memory import EpisodicMemory, Episode
from .learning.performance_metrics import PerformanceMetrics
from .learning.outcome_feedback import OutcomeFeedbackLoop
from .validation.identity_validator import IdentityValidator
from hse.simulation.synthetic_human_sim import SyntheticHumanSimulation
from ml.pattern_extraction import PatternExtractor

# NEW: Mode orchestrator for decision pipeline control
from .modes.mode_orchestrator import ModeOrchestrator
from .modes.mode_metrics import ModeMetrics

# NEW: Dynamic council for mode-aware council invocation
from .council.dynamic_council import DynamicCouncil

# Thread pool
executor = ThreadPoolExecutor(max_workers=4)

# Domain latch thresholds
DOMAIN_OVERRIDE_THRESHOLD = 0.45
FORCE_GUESS_TURNS = 2

# Background analysis wait when debugging (seconds)
BG_WAIT = float(os.getenv("PERSONA_BG_WAIT", "1.0"))

FAST_PATH = True


def _background_analysis(llm: Any, user_input: str, response: str, state: CognitiveState):
    """
    Runs the silent handshakes and updates state for the NEXT turn.
    Stores results into state so the main loop can consult them synchronously
    if needed for control decisions.
    """
    try:
        # situation
        situation = assess_situation(llm, user_input)
        state.last_situation = situation
        state.last_emotional_load = situation.get("emotional_load", 0.0)
        trace("background_situation", situation)

        # mode fitness
        mode_eval = assess_mode_fitness(llm, user_input, state.mode)
        state.last_mode_eval = mode_eval
        trace("background_mode_eval", mode_eval)

        # emotional metrics
        emo = assess_emotional_metrics(llm, user_input)
        state.emotional_metrics = emo
        trace("background_emotional_metrics", emo)

        # domain classification (force guess logic)
        convo_excerpt = "\n\n".join([u for u, a in state.recent_turns[-6:]] + [user_input])
        force_guess = False
        if not state.domains and (state.turn_count - (getattr(state, "last_domain_classification_turn", -999)) >= FORCE_GUESS_TURNS):
            force_guess = True

        domains_out = classify_domains(llm, convo_excerpt, force_guess=force_guess)
        trace("background_domains_raw", domains_out)

        d_conf = float(domains_out.get("confidence", 0.0) or 0.0)
        doms = domains_out.get("domains") or []
        if doms and (d_conf >= DOMAIN_OVERRIDE_THRESHOLD or force_guess):
            state.domains = doms
            # Ensure confidence is at least 0.5 when domains are latched (minimum meaningful confidence)
            state.domain_confidence = max(d_conf, 0.5)
            state.domains_locked = True
            state.last_domain_latched_at_turn = state.turn_count
            trace("domain_latched", {"domains": doms, "confidence": state.domain_confidence})

        # KIS: trigger when domains present and emotional advice_threshold (or high confidence)
        try:
            advice_signal = float(state.emotional_metrics.get("advice_threshold", 0.0) or 0.0)
        except Exception:
            advice_signal = 0.0

        if state.domains and (advice_signal >= 0.7 or state.domain_confidence > 0.0):
            try:
                kis = synthesize_knowledge(user_input=user_input, active_domains=state.domains, domain_confidence=max(state.domain_confidence, 0.5))
                state.background_knowledge = kis
                trace("background_kis_generated", {"num_items": len(kis.get("synthesized_knowledge", []))})
            except Exception as e:
                trace("background_kis_error", {"error": str(e)})

        # mark classification turn
        state.last_domain_classification_turn = state.turn_count

    except Exception as e:
        trace("background_analysis_failure", {"error": str(e)})


def _mca_decision(council: CouncilAggregator, prime: PrimeConfident, user_input: str, response: str, state: CognitiveState, mode_orchestrator: Optional[ModeOrchestrator] = None, dynamic_council: Optional[DynamicCouncil] = None) -> Dict[str, Any]:
    """
    Run Ministerial Cognitive Architecture decision loop.
    
    1. Determine which ministers to invoke based on decision mode
    2. Convene the selected ministers
    3. Aggregate their recommendations
    4. Prime Confident makes final decision
    
    Returns: dict with decision info for display/logging
    """
    try:
        # Build context for ministers (use simple types only - avoid nesting dicts as values initially)
        context = {
            "domains": state.domains or [],
            "turn_count": state.turn_count,
            "emotional_intensity": float(state.emotional_metrics.get("emotional_intensity", 0.0) if state.emotional_metrics else 0.0),
            "mode": state.mode,
        }
        # Store recent turns as string summary to avoid serialization issues
        recent_summary = "; ".join([u[:50] + "..." if len(u) > 50 else u for u, a in state.recent_turns[-3:]]) if state.recent_turns else ""
        context["recent_context"] = recent_summary
        
        # NEW: Determine which ministers to invoke based on mode
        if mode_orchestrator:
            current_mode = mode_orchestrator.get_current_mode()
            should_convene = mode_orchestrator.should_invoke_council(current_mode)
            ministers_to_invoke = mode_orchestrator.get_ministers_for_mode(current_mode, context)
            mode_framing = mode_orchestrator.frame_for_mode(user_input, current_mode, context)
            
            trace("mca_mode_routing", {
                "mode": current_mode,
                "should_convene": should_convene,
                "ministers": str(ministers_to_invoke)  # Convert to string to avoid hashability issues
            })
            
            # If mode says no council, return early with direct LLM response
            if not should_convene:
                trace("mca_mode_no_council", {"mode": current_mode})
                return {
                    "decision": "direct_response",
                    "mode": current_mode,
                    "ministers_invoked": [],
                    "reasoning": "Mode does not require ministerial council"
                }
        
        # Convene the council (using DynamicCouncil if available for mode-aware behavior)
        council_rec = None
        try:
            if dynamic_council:
                # Use mode-aware dynamic council
                council_rec_dict = dynamic_council.convene_for_mode(
                    current_mode,
                    user_input,
                    context
                )
                # Convert to CouncilRecommendation for compatibility
                from .council import CouncilRecommendation
                consensus_strength = float(council_rec_dict.get("consensus_strength", 0.5) or 0.5)
                council_rec = CouncilRecommendation(
                    outcome=council_rec_dict.get("outcome", "unknown"),
                    recommendation=council_rec_dict.get("recommendation", "unknown"),
                    avg_confidence=consensus_strength,
                    reasoning=council_rec_dict.get("reasoning", ""),
                    minister_positions=council_rec_dict.get("minister_positions", {}),
                    consensus_strength=consensus_strength,
                    dissenting_ministers=council_rec_dict.get("dissenting_ministers", []),
                    red_line_concerns=council_rec_dict.get("red_line_concerns", [])
                )
            else:
                # Fallback to legacy council
                council_rec = council.convene(user_input, context)
        except Exception as e:
            trace("council_convene_error", {"error": str(e)})
            council_rec = None
        
        if council_rec is None:
            # Fallback: no council recommendation available
            return {
                "error": "council_unavailable",
                "prime_final_decision": "defer"
            }
        
        trace("mca_council_recommendation", {
            "outcome": council_rec.outcome,
            "recommendation": str(council_rec.recommendation)[:100],
            "avg_confidence": float(council_rec.avg_confidence or 0.5),
            "red_line_count": len(council_rec.red_line_concerns or [])
        })
        
        # Prepare minister outputs for Prime Confident
        minister_outputs = {}
        if council_rec.minister_positions:
            for domain_name, position in council_rec.minister_positions.items():
                try:
                    minister_outputs[domain_name] = {
                        "stance": str(position.stance) if hasattr(position, 'stance') else "unknown",
                        "confidence": float(position.confidence if hasattr(position, 'confidence') else 0.5),
                        "reasoning": str(position.reasoning)[:100] if hasattr(position, 'reasoning') else "",
                        "red_line_triggered": bool(position.red_line_triggered) if hasattr(position, 'red_line_triggered') else False,
                    }
                except Exception as e:
                    trace("minister_position_conversion_error", {"domain": domain_name, "error": str(e)})
        
        # Prime Confident decides
        try:
            final_decision = prime.decide(
                council_recommendation={
                    "outcome": council_rec.outcome,
                    "recommendation": str(council_rec.recommendation)[:100],
                    "avg_confidence": float(council_rec.avg_confidence or 0.5),
                    "reasoning": str(council_rec.reasoning)[:100],
                    "consensus_strength": float(council_rec.consensus_strength or 0.5),
                },
                minister_outputs=minister_outputs
            )
        except Exception as e:
            trace("prime_decision_error", {"error": str(e)})
            final_decision = {"final_outcome": "defer", "reason": "prime_decision_failed"}
        
        trace("mca_prime_decision", {"outcome": final_decision.get("final_outcome"), "reason": final_decision.get("reason")})
        
        # Store MCA decision in state for potential context incorporation
        state.last_mca_decision = final_decision
        state.last_council_recommendation = council_rec
        
        return {
            "council_outcome": str(council_rec.outcome)[:50],
            "council_recommendation": str(council_rec.recommendation)[:50],
            "prime_final_decision": final_decision.get("final_outcome"),
            "prime_reason": final_decision.get("reason"),
            "red_line_triggered": bool(len(council_rec.red_line_concerns or []) > 0),
            "consensus_strength": float(council_rec.consensus_strength or 0.5),
        }
    
    except Exception as e:
        trace("mca_decision_error", {"error": str(e)})
        return {"error": str(e), "prime_final_decision": "defer"}


def validate_mode_coherence(mode: str, response: str, council_result: Dict) -> Dict[str, Any]:
    """
    Check if response matches the mode's requirements and expectations.
    
    QUICK mode: Should be personal, direct, no council references
    WAR mode: Should emphasize winning, speed, advantage, strategy
    MEETING mode: Should show balanced debate and synthesis of multiple views
    DARBAR mode: Should reference full deliberation and consensus
    """
    is_valid = True
    warning = ""
    
    if mode == "quick":
        # Quick mode should be personal and direct, not council-driven
        council_keywords = ["minister", "council", "deliberat", "conven", "assembled"]
        if any(kw in response.lower() for kw in council_keywords):
            is_valid = False
            warning = "Quick mode response mentioned council/ministers (should be personal and direct)"
    
    elif mode == "war":
        # War mode should emphasize winning, speed, advantage, aggressive positioning
        war_keywords = ["win", "advantage", "fast", "aggressive", "strategic", "dominat", "seize", "power", "overcome", "decisive"]
        has_war_language = any(kw in response.lower() for kw in war_keywords)
        
        if not has_war_language:
            is_valid = False  # Set to warning-level (don't hard-fail)
            warning = "War mode response could emphasize winning/advantage more (score: victory-focused language)"
    
    elif mode == "meeting":
        # Meeting mode should show debate/synthesis - involve multiple perspectives
        ministers = council_result.get("ministers_involved", [])
        if len(ministers) < 2:
            is_valid = False
            warning = f"Meeting mode should involve multiple ministers for debate (only {len(ministers)} involved)"
        
        # Should synthesize or show balanced perspectives
        synthesis_keywords = ["balanc", "consider", "both", "tradeoff", "however", "yet", "deliberat", "weigh"]
        if not any(kw in response.lower() for kw in synthesis_keywords):
            warning = "Meeting mode response could better show synthesis of different perspectives"
    
    elif mode == "darbar":
        # Darbar mode should reference full deliberation and significant council involvement
        ministers = council_result.get("ministers_involved", [])
        if len(ministers) < 10:
            is_valid = False
            warning = f"Darbar mode should involve significant portion of council (only {len(ministers)}/18 involved)"
        
        # Should reference council wisdom, consensus, or doctrine
        darbar_keywords = ["council", "consensus", "doctrine", "wisdom", "deliber", "ministers", "convened"]
        if not any(kw in response.lower() for kw in darbar_keywords):
            warning = "Darbar mode response could reference council consensus or doctrine alignment"
    
    return {
        "is_valid": is_valid,
        "warning": warning,
        "mode": mode,
        "validation_passed": is_valid
    }


def main():
    print("[MAIN] Starting main function...", file=sys.stderr, flush=True)
    
    state = CognitiveState()
    state.mode_ttl = MODE_INERTIA.get(state.mode, 1)

    # create brain and llm
    print("[MAIN] Creating brain...", file=sys.stderr, flush=True)
    brain = PersonaBrain()
    
    print("[MAIN] Initializing LLM runtime...", file=sys.stderr, flush=True)
    
    # Instantiate LLM runtime with graceful fallback to sovereign adapter
    try:
        from .ollama_runtime import OllamaRuntime
        print("[MAIN] Trying OllamaRuntime...", file=sys.stderr, flush=True)
        llm = OllamaRuntime()
        print("[MAIN] OllamaRuntime initialized", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[MAIN] OllamaRuntime failed: {e}", file=sys.stderr, flush=True)
        try:
            from sovereign.llm_adapter import OllamaAdapter
            print("[MAIN] Trying OllamaAdapter...", file=sys.stderr, flush=True)
            llm = OllamaAdapter()
            print("[MAIN] OllamaAdapter initialized", file=sys.stderr, flush=True)
        except Exception as e:
            print("FATAL: No LLM runtime available:", e)
            sys.exit(1)
    
    # Initialize MCA components
    print("[MAIN] Initializing council and orchestrators...", file=sys.stderr, flush=True)
    council = CouncilAggregator(llm=llm)
    prime = PrimeConfident(risk_threshold=0.7)

    # NEW: Initialize mode orchestrator
    mode_orchestrator = ModeOrchestrator()
    
    # NEW: Initialize dynamic council (mode-aware wrapper)
    dynamic_council = DynamicCouncil(llm=llm)
    
    # NEW: Initialize mode metrics tracking
    mode_metrics = ModeMetrics()
    
    # NEW: Initialize learning systems
    print("[MAIN] Initializing learning systems...", file=sys.stderr, flush=True)
    episodic_memory = EpisodicMemory(storage_path="data/memory/episodes.jsonl")
    metrics = PerformanceMetrics(storage_path="data/memory/metrics.jsonl")
    feedback_loop = OutcomeFeedbackLoop(council=council, kis_engine=None, episodic_memory=episodic_memory)
    identity_validator = IdentityValidator(persona_doctrine=None)
    pattern_extractor = PatternExtractor(episodic_memory=episodic_memory)
    
    # NEW: Initialize synthetic human simulation (if enabled)
    print(f"[MAIN] AUTOMATED_SIMULATION={os.getenv('AUTOMATED_SIMULATION')}", file=sys.stderr, flush=True)
    AUTOMATED_SIMULATION = os.getenv("AUTOMATED_SIMULATION", "0") == "1"
    print(f"[MAIN] Parsed AUTOMATED_SIMULATION={AUTOMATED_SIMULATION}", file=sys.stderr, flush=True)
    
    if AUTOMATED_SIMULATION:
        print("[MAIN] Initializing synthetic human...", file=sys.stderr, flush=True)
        try:
            from hse.human_profile import SyntheticHuman
            synthetic_human = SyntheticHuman(name="Test Subject", age=32, seed=42)
            human_sim = SyntheticHumanSimulation(synthetic_human, user_llm=llm)
            print("[SIMULATION] Automated synthetic human enabled.\n", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[WARNING] Could not initialize synthetic human: {e}", file=sys.stderr, flush=True)
            AUTOMATED_SIMULATION = False
    else:
        print("[MAIN] Synthetic simulation disabled", file=sys.stderr, flush=True)
        human_sim = None

    # NEW: Mode selection at startup
    print("\n" + "="*60)
    print("PERSONA N - DECISION MODE SELECTION")
    print("="*60)
    
    # Auto-select mode if automated simulation is enabled
    if AUTOMATED_SIMULATION:
        selected_mode = "meeting"  # Default to meeting mode for simulation
        print(f"\n[SIMULATION] Auto-selected MEETING mode for synthetic conversation\n")
    else:
        print("\nSelect your decision-making mode:")
        print("  [1] QUICK MODE      - 1:1 mentoring (personal, fast, no council)")
        print("  [2] WAR MODE        - Victory-focused (aggressive, Risk/Power/Strategy)")
        print("  [3] MEETING MODE    - Balanced debate (3-5 relevant ministers)")
        print("  [4] DARBAR MODE     - Full council wisdom (all 18 ministers)")
        print()
        
        mode_choice = input("Enter mode [1-4] (default: 3/MEETING): ").strip()
        mode_map = {"1": "quick", "2": "war", "3": "meeting", "4": "darbar"}
        selected_mode = mode_map.get(mode_choice, "meeting")
    
    mode_orchestrator.set_mode(selected_mode)
    dynamic_council.set_mode(selected_mode)
    
    print(f"\nMode: {selected_mode.upper()} - {mode_orchestrator.get_mode_description(selected_mode)}")
    print("="*60)
    print("\nTypes: 'exit' to quit | '/mode quick|war|meeting|darbar' to switch modes")
    print("\nPersona N online (with Ministerial Cognitive Architecture).\n")

    last_response = ""  # Initialize before loop
    context_for_simulation = {}  # Initialize context for entire loop

    while True:
        # NEW: Get user input (synthetic or real)
        if AUTOMATED_SIMULATION:
            try:
                # Prepare context for synthetic human
                context_for_simulation = {
                    "mode": state.mode,
                    "domains": state.domains or [],
                    "turn_count": state.turn_count,
                    "recent_turns": list(state.recent_turns[-3:]) if state.recent_turns else [],
                }
                user_input = human_sim.generate_next_input(last_response, context_for_simulation)
                print(f"> [SYNTHETIC USER] {user_input}\n")
            except Exception as e:
                print(f"[ERROR] Synthetic input generation failed: {e}")
                user_input = input("> ").strip()
        else:
            user_input = input("> ").strip()
        
        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("\nN: We'll continue another time.\n")
            break
        
        # NEW: Handle mode switching commands
        if user_input.lower().startswith("/mode "):
            requested_mode = user_input[6:].strip().lower()
            if mode_orchestrator.set_mode(requested_mode):
                dynamic_council.set_mode(requested_mode)  # Sync dynamic council with new mode
                desc = mode_orchestrator.get_mode_description(requested_mode)
                print(f"\n[MODE] Switched to {requested_mode.upper()} - {desc}\n")
                if mode_orchestrator.should_invoke_council(requested_mode):
                    ministers = mode_orchestrator.get_ministers_for_mode(requested_mode, {"domains": state.domains})
                    print(f"[MODE] Ministers: {', '.join(ministers)}\n")
                else:
                    print(f"[MODE] Direct LLM response (no council).\n")
            else:
                print(f"\n[MODE ERROR] Unknown mode '{requested_mode}'. Available: {', '.join(mode_orchestrator.list_modes())}\n")
            continue

        # If we are awaiting clarification, clear awaiting flag when user replies
        if getattr(state, "awaiting_clarification", False):
            trace("clarification_answer_received", {"expected": getattr(state, "expected_clarification", None), "answer": user_input})
            state.awaiting_clarification = False
            state.expected_clarification = None

        state.turn_count += 1
        
        # Ensure we run a synchronous situation check every turn so state is populated for observer/brain.
        try:
            future = executor.submit(assess_situation, llm, user_input)
            try:
                raw_sit = future.result(timeout=1.0)
            except TimeoutError:
                raw_sit = assess_situation_heuristic(user_input)
            # Defensive normalization: ensure keys exist
            if not isinstance(raw_sit, dict):
                raw_sit = assess_situation_heuristic(user_input)
            situation_type = raw_sit.get("situation_type") or raw_sit.get("type") or "unclear"
            clarity = float(raw_sit.get("clarity", raw_sit.get("clarity_score", 0.0) or 0.0))
            emotional_load = float(raw_sit.get("emotional_load", raw_sit.get("emotion", 0.0) or 0.0))
            # store normalized
            state.last_situation = {"situation_type": situation_type, "clarity": clarity, "emotional_load": emotional_load}
            state.last_emotional_load = emotional_load
            trace("sync_situation_result", state.last_situation)
        except Exception as e:
            # fallback safe defaults
            state.last_situation = {"situation_type": "unclear", "clarity": 0.0, "emotional_load": 0.0}
            state.last_emotional_load = 0.0
            trace("sync_situation_error", {"error": str(e)})
        state.user_frequency = (lambda s: "low" if len(s.split()) <= 3 else ("medium" if len(s.split()) <= 12 else "high"))(user_input)

        system_context = build_system_context(state)

        # Primary speak (user-visible) — FAST_PATH immediate reply
        response = llm.speak(system_context, user_input)

        # Bookkeeping
        state.recent_turns.append((user_input, response))
        if len(state.recent_turns) > 50:
            state.recent_turns = state.recent_turns[-50:]
        
        # IMPROVEMENT: Ensure emotional metrics and domain confidence are captured from response analysis
        # This enables multi-turn state persistence (critical for LLM integration)
        if hasattr(state, 'emotional_metrics') and state.emotional_metrics:
            state.last_emotional_load = float(state.emotional_metrics.get('emotional_intensity', state.last_emotional_load))
        
        # Persist domain knowledge from analysis into state for next turn
        if hasattr(state, 'background_knowledge') and state.background_knowledge:
            bg_ks = state.background_knowledge.get('synthesized_knowledge', [])
            if bg_ks and not state.domains:
                # Extract domains from KIS if not already classified
                ks_trace = state.background_knowledge.get('knowledge_trace', [])
                inferred_domains = list(set([d.get('domain') for d in ks_trace if d.get('domain')]))
                if inferred_domains:
                    state.domains = inferred_domains
        
        # Ensure confidence is persisted across turns
        if hasattr(state, 'domain_confidence') and state.domain_confidence == 0.0 and state.domains:
            state.domain_confidence = 0.5  # Default confidence when domains are present

        # Capture pending offer text if any
        if state.pending_mode_suggestion and state.mode_offer_made and not state.pending_offer_text:
            state.pending_offer_text = response

        # Display assistant response
        display = trim_response(response, state.mode)
        display = enforce_frequency(display, state.user_frequency)
        label = f"[{state.mode.upper()}] "
        print(f"\nN: {label}{display}\n")
        
        # Store response for synthetic human loop
        last_response = response
        
        # NEW: Validate mode coherence (check response matches mode expectations)
        mode_validation_result = {}
        try:
            council_result = getattr(state, 'last_council_recommendation', {}) or {}
            mode_validation_result = validate_mode_coherence(state.mode, response, council_result)
            if not mode_validation_result.get("is_valid", True):
                print(f"[⚠️  MODE] {mode_validation_result.get('warning', 'Mode validation check failed')}")
        except Exception as e:
            trace("mode_validation_error", {"error": str(e)})
        
        # NEW: Validate identity consistency
        try:
            coherent, contradiction = identity_validator.check_self_contradiction(state.turn_count, response)
            if not coherent:
                print(f"[⚠️  IDENTITY] Warning: {contradiction}")
                identity_validator.log_contradiction(state.turn_count, contradiction, response, "")
        except Exception as e:
            trace("identity_validation_error", {"error": str(e)})
        
        # NEW: Store episode in episodic memory
        episode = None
        try:
            domain = state.domains[0] if state.domains else "general"
            episode = Episode(
                episode_id=None,
                turn_id=state.turn_count,
                domain=domain,
                user_input=user_input[:200],  # Limit input length
                persona_recommendation=response[:200],  # Limit recommendation length
                confidence=float(state.domain_confidence if hasattr(state, 'domain_confidence') else 0.5),
                minister_stance="unknown",  # Simplified to avoid dict key issues
                council_recommendation="unknown",  # Simplified to avoid dict key issues
            )
            episodic_memory.store_episode(episode)
            
            # NEW: Check for pattern repetition
            try:
                past_mistake = feedback_loop.detect_repeated_mistake(episode)
                if past_mistake:
                    print(f"[⚠️  MEMORY] Repeating mistake from turn {past_mistake.turn_id}: {past_mistake.domain}")
            except Exception as e:
                trace("pattern_detection_error", {"error": str(e)})
        except Exception as e:
            trace("episode_storage_error", {"error": str(e)})
        
        # NEW: Apply consequences if synthetic human is running
        if AUTOMATED_SIMULATION and human_sim:
            try:
                outcome_info = human_sim.apply_consequences(
                    state.domain_confidence if hasattr(state, 'domain_confidence') else 0.5,
                    state.domains[0] if state.domains else "general"
                )
                # Record outcome in episodic memory
                if 'episode' in locals():
                    episode.outcome = outcome_info.get("outcome")
                    episode.regret_score = outcome_info.get("regret_score", 0.0)
                    feedback_loop.record_decision_outcome(episode)
                    
                    # Periodic retraining: every 50 turns check for failure clusters
                    if state.turn_count % 50 == 0:
                        failure_clusters = episodic_memory.detect_failure_clusters()
                        for cluster_name, failures in failure_clusters.items():
                            if len(failures) > 2:
                                cluster_domain = cluster_name.split("_")[0]
                                feedback_loop.retrain_ministers(cluster_domain, failures)
            except Exception as e:
                trace("synthetic_consequences_error", {"error": str(e)})
        
        # NEW: Record metrics
        try:
            metrics.record_decision(
                turn=state.turn_count,
                domain=state.domains[0] if state.domains else "general",
                recommendation=response[:100],
                confidence=state.domain_confidence if hasattr(state, 'domain_confidence') else 0.5,
                outcome=episode.outcome if 'episode' in locals() else None,
                regret=episode.regret_score if 'episode' in locals() else 0.0
            )
        except Exception as e:
            trace("metrics_recording_error", {"error": str(e)})
        
        # NEW: Periodic reporting (every 100 turns)
        if state.turn_count % 100 == 0:
            try:
                weak_domains = metrics.detect_weak_domains(threshold=0.5)
                stability = metrics.measure_stability(window=100)
                improvement = metrics.show_improvement_trajectory(window=100)
                coverage = metrics.get_feature_coverage()
                success_rate = metrics.get_success_rate()
                
                # NEW: Extract patterns and generate learning signals
                patterns = pattern_extractor.extract_patterns(num_episodes=100)
                learning_signals = pattern_extractor.generate_learning_signals()
                pattern_extractor.save_patterns()
                
                print(f"\n{'='*60}")
                print(f"TURN {state.turn_count} METRICS & LEARNING SIGNALS")
                print(f"{'='*60}")
                print(f"Overall success rate: {success_rate:.1%}")
                print(f"Weak domains (success < 50%): {weak_domains}")
                print(f"Stability score: {stability.get('stability_score', 0.0):.1%}")
                print(f"Improvement trajectory: +{improvement.get('percent_improvement', 0):.1f}%")
                print(f"Feature coverage: {coverage}")
                print(f"Episodic memory size: {len(episodic_memory.episodes)}")
                
                # Print learning signals
                if learning_signals.get("weak_domains"):
                    print(f"\n📊 WEAK DOMAINS (need improvement):")
                    for domain_info in learning_signals["weak_domains"]:
                        print(f"  - {domain_info['domain']}: {domain_info['success_rate']:.1%} success")
                
                if learning_signals.get("sequential_risks"):
                    print(f"\n⚠️  SEQUENTIAL RISKS:")
                    for risk in learning_signals["sequential_risks"]:
                        print(f"  - {risk['type']}: {risk['length']} turns")
                
                # NEW: Print mode performance comparison
                try:
                    mode_comparison = mode_metrics.compare_modes()
                    if mode_comparison:
                        print(f"\n🎯 MODE PERFORMANCE COMPARISON:")
                        for mode_perf in mode_comparison:
                            mode_name = mode_perf.get("mode", "unknown").upper()
                            success_rate = mode_perf.get("success_rate", 0.0)
                            turns = mode_perf.get("turns", 0)
                            avg_confidence = mode_perf.get("avg_confidence", 0.0)
                            if turns > 0:
                                print(f"  {mode_name:12} - {success_rate:6.1%} success | {turns:3} turns | {avg_confidence:.2f} avg confidence")
                except Exception as e:
                    trace("mode_metrics_reporting_error", {"error": str(e)})
                
                print(f"{'='*60}\n")
            except Exception as e:
                trace("metrics_reporting_error", {"error": str(e)})

        # Run MCA decision (Ministerial Cognitive Architecture)
        # This convenes the council (or skips it based on mode) and Prime Confident determines meta-level action
        try:
            mca_decision = _mca_decision(council, prime, user_input, response, state, mode_orchestrator, dynamic_council)
            trace("mca_completed", mca_decision)
            
            # NEW: Record mode-specific metrics
            try:
                # Determine outcome based on red line and consensus
                mca_outcome = "success" if mca_decision.get("prime_final_decision") != "reject" else "failure"
                
                # Use consensus strength as confidence metric
                consensus = mca_decision.get("consensus_strength", 0.5)
                
                # Estimate regret based on red line concerns
                regret = 0.1 if mca_decision.get("red_line_triggered") else 0.0
                
                mode_metrics.record_mode_decision(
                    mode=state.mode,
                    outcome=mca_outcome,
                    confidence=consensus,
                    regret=regret
                )
            except Exception as e:
                trace("mode_metrics_recording_error", {"error": str(e)})
            
            # If Prime Confident rejected (red line), add warning comment
            if mca_decision.get("prime_final_decision") == "reject":
                print("[MCA] ⚠️  Red line concern. Prime Confident has flagged this response.\n")
                trace("mca_red_line_warning", mca_decision)
            elif mca_decision.get("red_line_triggered"):
                print("[MCA] ⚠️  Council raised concerns. Proceeding with caution.\n")
        except Exception as e:
            trace("mca_execution_error", {"error": str(e)})

        # Launch background analysis (silent handshakes)
        try:
            bg_future: Future = executor.submit(_background_analysis, llm, user_input, response, state)
            if DEBUG_OBSERVER:
                try:
                    bg_future.result(timeout=BG_WAIT)
                    trace("background_analysis_completed_sync_wait", {"turn": state.turn_count})
                except Exception:
                    trace("background_analysis_not_completed_in_wait", {"turn": state.turn_count})
        except Exception as e:
            trace("background_analysis_submit_error", {"error": str(e)})

        # Now: run control decision synchronously using fresh coherence/situation where possible
        try:
            # Synchronous short handshakes to feed the brain
            # These are small targeted calls to ensure control has the inputs it needs
            situation = None
            coherence = None
            try:
                situation = assess_situation(llm, user_input)
                state.last_situation = situation
            except Exception as e:
                trace("sync_situation_error", {"error": str(e)})

            try:
                coherence = assess_coherence(llm, user_input)
                state.last_coherence = coherence
            except Exception as e:
                trace("sync_coherence_error", {"error": str(e)})

            # Prepare plain dict for brain.decide (brain expects dict-like state)
            state_snapshot = {
                "mode": state.mode,
                "domains": state.domains,
                "domain_confidence": state.domain_confidence,
                "turn_count": state.turn_count,
                "user_frequency": state.user_frequency,
            }

            decision = brain.decide(coherence=coherence, situation=situation or {}, state=state_snapshot)
            trace("brain_decision", {"decision": decision.__dict__ if hasattr(decision, "__dict__") else str(decision)})

            # If the brain asked to 'ask', build and ask the clarifying question
            if decision and getattr(decision, "action", None) == "ask":
                # Generate a short list of clarifying questions via LLM (fallbacks applied in generator)
                qs = []
                try:
                    qs = generate_clarifying_questions(llm, user_input, max_questions=3, context=(state.last_situation or {}))
                except Exception as e:
                    trace("generate_clarifying_questions_error", {"error": str(e)})

                if not qs:
                    # Fallback to older single-question builder
                    q_text = build_clarifying_question(decision, state)
                    qs = [{"id": "q1", "question": q_text, "reason": "fallback", "expected_answer_type": "short"}]

                # Iteratively ask questions, collect answers, and re-run KIS until quality threshold or max rounds
                collected_answers: list[str] = []
                MAX_ROUNDS = getattr(state, "max_clarify_rounds", 3)
                QUALITY_THRESHOLD = 0.6
                round_idx = 0
                last_quality = 0.0

                for qobj in qs[:MAX_ROUNDS]:
                    if round_idx >= MAX_ROUNDS:
                        break
                    round_idx += 1

                    q_display = format_question_for_user(qobj, state)
                    ask_system_context = system_context + "\n\nOVERRIDE: For this single response, you MAY ask a short clarifying question exactly as provided."
                    ask_response = llm.speak(ask_system_context, q_display)

                    # show assistant asking the clarifier
                    print(f"\nN: [CLARIFY] {ask_response}\n")
                    trace("clarify_asked", {"question": q_display, "assistant": ask_response, "round": round_idx})

                    # Collect user's answer synchronously
                    try:
                        if AUTOMATED_SIMULATION and human_sim:
                            # In simulation mode, have synthetic human answer the clarifying question
                            user_answer = human_sim.generate_next_input(ask_response, context_for_simulation)
                            print(f"> [SYNTHETIC USER] {user_answer}\n")
                        else:
                            user_answer = input(">> ").strip()
                    except Exception:
                        user_answer = ""

                    trace("clarify_answer_collected", {"question": q_display, "answer": user_answer, "round": round_idx})
                    collected_answers.append(user_answer)

                    # Re-run KIS synthesizer with collected answers as extra_context
                    try:
                        kis_out = synthesize_knowledge(user_input=user_input, active_domains=state.domains or [], domain_confidence=state.domain_confidence or 0.0, extra_context=collected_answers)
                        # expect knowledge_quality in return
                        kq = kis_out.get("knowledge_quality") or {}
                        last_quality = float(kq.get("candidate_quality", 0.0) or 0.0)
                        trace("clarify_kis_result", {"round": round_idx, "knowledge_quality": kq})
                    except Exception as e:
                        trace("clarify_kis_error", {"error": str(e)})
                        last_quality = 0.0

                    # Stop early if quality threshold reached
                    if last_quality >= QUALITY_THRESHOLD:
                        trace("clarify_quality_satisfied", {"round": round_idx, "quality": last_quality})
                        break

                # After loop, update state with collected answers and last quality
                state.collected_answers = (getattr(state, "collected_answers", []) or []) + collected_answers
                state.last_knowledge_quality = last_quality
                # If not high quality, set awaiting flag so brain can escalate or ask again later
                if last_quality < QUALITY_THRESHOLD:
                    state.awaiting_clarification = True
                    state.expected_clarification = qs[0] if qs else None
                else:
                    state.awaiting_clarification = False
                    state.expected_clarification = None
        except Exception as e:
            trace("control_decision_error", {"error": str(e)})

        # Finally print traces (if enabled)
        print_trace()


if __name__ == "__main__":
    main()
