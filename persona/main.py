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
from ..sovereign.prime_confident import PrimeConfident

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


def _mca_decision(council: CouncilAggregator, prime: PrimeConfident, user_input: str, response: str, state: CognitiveState) -> Dict[str, Any]:
    """
    Run Ministerial Cognitive Architecture decision loop.
    
    1. Convene the council of ministers
    2. Aggregate their recommendations
    3. Prime Confident makes final decision
    
    Returns: dict with decision info for display/logging
    """
    try:
        # Build context for ministers
        context = {
            "domains": state.domains or [],
            "turn_count": state.turn_count,
            "recent_turns": state.recent_turns[-6:] if state.recent_turns else [],
            "emotional_metrics": state.emotional_metrics or {},
            "mode": state.mode,
        }
        
        # Convene the council
        council_rec = council.convene(user_input, context)
        trace("mca_council_recommendation", {
            "outcome": council_rec.outcome,
            "recommendation": council_rec.recommendation,
            "avg_confidence": council_rec.avg_confidence,
            "red_lines": council_rec.red_line_concerns
        })
        
        # Prepare minister outputs for Prime Confident
        minister_outputs = {}
        for domain_name, position in council_rec.minister_positions.items():
            minister_outputs[domain_name] = {
                "stance": position.stance,
                "confidence": position.confidence,
                "reasoning": position.reasoning,
                "red_line_triggered": position.red_line_triggered,
            }
        
        # Prime Confident decides
        final_decision = prime.decide(
            council_recommendation={
                "outcome": council_rec.outcome,
                "recommendation": council_rec.recommendation,
                "avg_confidence": council_rec.avg_confidence,
                "reasoning": council_rec.reasoning,
                "consensus_strength": council_rec.consensus_strength,
            },
            minister_outputs=minister_outputs
        )
        
        trace("mca_prime_decision", final_decision)
        
        # Store MCA decision in state for potential context incorporation
        state.last_mca_decision = final_decision
        state.last_council_recommendation = council_rec
        
        return {
            "council_outcome": council_rec.outcome,
            "council_recommendation": council_rec.recommendation,
            "prime_final_decision": final_decision.get("final_outcome"),
            "prime_reason": final_decision.get("reason"),
            "red_line_triggered": len(council_rec.red_line_concerns) > 0,
            "consensus_strength": council_rec.consensus_strength,
        }
    
    except Exception as e:
        trace("mca_decision_error", {"error": str(e)})
        return {"error": str(e), "prime_final_decision": "defer"}



def main():
    state = CognitiveState()
    state.mode_ttl = MODE_INERTIA.get(state.mode, 1)

    # create brain and llm
    brain = PersonaBrain()
    # Instantiate LLM runtime with graceful fallback to sovereign adapter
    try:
        from .ollama_runtime import OllamaRuntime
        llm = OllamaRuntime()
    except Exception:
        try:
            from ..sovereign.llm_adapter import OllamaAdapter
            llm = OllamaAdapter()
        except Exception as e:
            print("FATAL: No LLM runtime available:", e)
            sys.exit(1)
    
    # Initialize MCA components
    council = CouncilAggregator(llm=llm)
    prime = PrimeConfident(risk_threshold=0.7)

    print("Persona N online (with Ministerial Cognitive Architecture). Type 'exit' to quit.\n")

    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("\nN: We’ll continue another time.\n")
            break

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

        # Run MCA decision (Ministerial Cognitive Architecture)
        # This convenes the council and Prime Confident determines meta-level action
        try:
            mca_decision = _mca_decision(council, prime, user_input, response, state)
            trace("mca_completed", mca_decision)
            
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