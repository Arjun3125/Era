"""
Advanced Decision Guidance System with Machine Learning

Intelligent multi-turn problem-solving engine with:
• Automatic or manual problem intake
• Domain detection (15 domains, stakes, reversibility)
• Multi-turn dialogue with automatic complexity escalation
• KIS synthesis (Knowledge Integration System - 40K+ doctrine items)
• Dynamic council invocation (QUICK/MEETING/WAR/DARBAR modes)
• Prime Confident final decision authority
• Episodic learning and performance tracking
• ML analysis and pattern extraction
• Session continuity and consequence tracking
• Real-time system improvement through learning

Core Flow:
  [Problem Input] → [Domain Analysis] → [Session Initialization]
         ↓
  [Multi-Turn Loop: KIS + Council + Prime Decision + Satisfaction]
         ↓
  [Episode Storage] → [ML Analysis] → [Learning Output]
         ↓
  [Pattern Recognition & System Improvement] → [Next Session]
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# IMPORTS
# ============================================================

from persona.ollama_runtime import OllamaRuntime
from persona.domain_detector import analyze_situation, domain_similarity
from persona.session_manager import SessionManager
from persona.modes.mode_orchestrator import ModeOrchestrator
from persona.knowledge_engine import synthesize_knowledge
from persona.council.dynamic_council import DynamicCouncil
from sovereign.prime_confident import PrimeConfident
from persona.learning.episodic_memory import EpisodicMemory, Episode
from persona.learning.performance_metrics import PerformanceMetrics


# ============================================================
# UNIFIED SYSTEM
# ============================================================

class DecisionGuidanceSystem:
    """
    Advanced decision guidance system with machine learning.
    
    Provides intelligent problem-solving through multi-turn dialogue,
    sophisticated council-based reasoning, and continuous improvement
    through episodic learning.
    """
    
    def __init__(self, auto_generate=True, verbose=True):
        """
        Initialize the system.
        
        Args:
            auto_generate: Automatically generate problems via LLM (True) or accept user input (False)
            verbose: Print detailed status messages
        """
        self.verbose = verbose
        self.auto_generate = auto_generate
        
        print("\n" + "="*70)
        print("🚀 ADVANCED DECISION GUIDANCE SYSTEM")
        print("="*70)
        
        # ===== Initialize LLMs =====
        print("\n[Init] Initializing LLM runtimes...")
        try:
            self.user_llm = OllamaRuntime(
                speak_model="deepseek-r1:8b",
                analyze_model="deepseek-r1:8b"
            )
            print("  ✓ User LLM (deepseek-r1:8b) ready")
        except Exception as e:
            print(f"  ✗ User LLM failed: {e}")
            self.user_llm = None
        
        try:
            self.program_llm = OllamaRuntime(
                speak_model="qwen3:14b",
                analyze_model="qwen3:14b"
            )
            print("  ✓ Program LLM (qwen3:14b) ready")
        except Exception as e:
            print(f"  ✗ Program LLM failed: {e}")
            self.program_llm = None
        
        # ===== Initialize Core Components =====
        print("\n[Init] Initializing core components...")
        
        self.session_manager = SessionManager(storage_dir="data/sessions")
        print("  ✓ SessionManager")
        
        self.mode_orchestrator = ModeOrchestrator()
        print("  ✓ ModeOrchestrator")
        
        self.dynamic_council = DynamicCouncil()
        print("  ✓ DynamicCouncil")
        
        self.prime_confident = PrimeConfident()
        print("  ✓ PrimeConfident")
        
        self.episodic_memory = EpisodicMemory(storage_path="data/memory/episodes.jsonl")
        print("  ✓ EpisodicMemory")
        
        self.performance_metrics = PerformanceMetrics(storage_path="data/memory/metrics.jsonl")
        print("  ✓ PerformanceMetrics")
        
        # ===== Tracking =====
        self.session_count = 0
        self.total_turns = 0
        self.learning_records = []
        self.session_history = []
        
        print("\n[Init] ✅ System fully initialized\n")
    
    # ============================================================
    # PROBLEM GENERATION/INPUT
    # ============================================================
    
    def _get_problem_statement(self) -> Optional[str]:
        """
        Obtain problem statement from user or generate via LLM.
        
        Returns:
            Problem statement string or None if user exits
        """
        if self.auto_generate and self.user_llm:
            return self._generate_problem_via_llm()
        else:
            return self._get_problem_from_user()
    
    def _generate_problem_via_llm(self) -> Optional[str]:
        """Generate a realistic problem via User LLM."""
        
        print("[Problem Generation] Creating realistic problem...")
        
        prompt = """Generate a realistic, specific personal or professional problem 
        that someone might seek guidance on. The problem should:
        1. Be specific and detailed (2-3 sentences)
        2. Have clear stakes and consequences
        3. Involve decision-making
        4. Be authentic to real human experience
        
        Examples of good problems:
        - "I've been offered a promotion but it requires relocating to a city where I have no connections. My spouse is nervous about the move. Should I take it?"
        - "My team member has been underperforming, and I need to decide whether to give them another chance or let them go."
        - "I'm considering a career change from engineering to teaching. Financially I can afford it, but I'm worried about making the wrong choice."
        
        Generate ONE unique problem now:"""
        
        try:
            response = self.user_llm.analyze(
                system_prompt="You are generating realistic personal problems for decision guidance.",
                user_prompt=prompt
            )
            return response.strip() if response else None
        except Exception as e:
            print(f"[ERROR] Problem generation failed: {e}")
            return None
    
    def _get_problem_from_user(self) -> Optional[str]:
        """Get problem statement from user via input."""
        
        try:
            problem = input("\n[Input] What's your problem or concern? (or 'exit' to quit)\n>> ").strip()
            
            if problem.lower() == "exit":
                return None
            
            if not problem:
                print("[Error] Problem cannot be empty")
                return self._get_problem_from_user()
            
            return problem
        
        except EOFError:
            return None
    
    # ============================================================
    # MAIN SESSION LOOP
    # ============================================================
    
    def run_session(self, problem_statement: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Run a complete problem-solving session.
        
        Flow:
        1. Get/generate problem statement
        2. Analyze and detect domains
        3. Check related previous sessions
        4. Loop: KIS → Council → Prime Decision → Satisfaction Check
        5. Store episode and metrics
        6. Run ML analysis
        
        Args:
            problem_statement: Explicit problem to use, or None to generate/ask
        
        Returns:
            Session result dictionary
        """
        
        self.session_count += 1
        
        print(f"\n{'='*70}")
        print(f"SESSION {self.session_count} - Unified Problem Solving")
        print(f"{'='*70}\n")
        
        # ===== PHASE 1: Problem Intake =====
        if problem_statement is None:
            problem_statement = self._get_problem_statement()
        
        if not problem_statement:
            print("[Info] No problem statement - exiting session")
            return None
        
        print(f"[Problem]\n{problem_statement}\n")
        
        # ===== PHASE 2: Domain Analysis =====
        print("[Phase 2] Analyzing problem for domains...")
        
        analysis = analyze_situation(problem_statement, llm_adapter=self.program_llm)
        
        domains = analysis.get("domains", ["strategy"])
        domain_confidence = analysis.get("domain_confidence", 0.75)
        stakes = analysis.get("stakes", "medium")
        reversibility = analysis.get("reversibility", "partially_reversible")
        
        print(f"  → Domains: {', '.join(domains)}")
        print(f"  → Stakes: {stakes} | Reversibility: {reversibility}")
        print(f"  → Confidence: {domain_confidence:.2%}\n")
        
        # ===== PHASE 3: Session Continuity Check =====
        print("[Phase 3] Checking related previous sessions...")
        
        related_sessions = self.session_manager.find_related_sessions(domains, limit=2)
        
        if related_sessions:
            print(f"  Found {len(related_sessions)} related session(s):")
            for prev in related_sessions:
                conclusion = (prev.final_conclusion or "inconclusive")[:50]
                print(f"    • {prev.problem_statement[:60]}... > {conclusion}...")
        else:
            print("  No related previous sessions")
        
        # ===== PHASE 4: Start Session =====
        print("\n[Phase 4] Starting session management...")
        
        session = self.session_manager.start_session(
            problem_statement=problem_statement,
            domains=domains if domains else ["strategy"],
            domain_confidence=domain_confidence,
            stakes=stakes,
            reversibility=reversibility,
            parent_session_id=related_sessions[0].session_id if related_sessions else None
        )
        
        print(f"  → Session ID: {session.session_id[-8:]}")
        
        # ===== PHASE 5: Multi-Turn Conversational Dialogue =====
        print(f"\n[Phase 5] Starting natural back-and-forth dialogue...\n")
        
        session_satisfied = False
        conversation_history = []
        final_decision = None
        final_confidence = 0.5
        dialogue_context = []  # Track conversation context
        
        # ===== CLARIFICATION PHASE: Prime asks questions, User LLM responds =====
        print("[Clarification Phase] Prime gathers more details about your situation...\n")
        
        clarification_rounds = min(3, 5)  # 3 rounds of clarification max
        
        for clarify_turn in range(1, clarification_rounds + 1):
            print(f"{'-'*70}")
            print(f"CLARIFICATION EXCHANGE {clarify_turn}")
            print(f"{'-'*70}")
            
            self.total_turns += 1
            
            # ===== Prime Asks Clarifying Questions =====
            print("[Prime Confident] Asking clarifying questions...\n")
            
            context_summary = "\n".join([f"  {entry['speaker']}: {entry['text'][:100]}..." for entry in dialogue_context[-4:]])
            
            prime_question_prompt = f"""You are Prime Confident, counselor and decision authority.

Original problem: "{problem_statement}"
Domains: {', '.join(domains)}
Stakes: {stakes}

Previous context:
{context_summary if context_summary else "  (Starting conversation)"}

Generate 2-3 specific, clarifying questions that will help you understand their situation better.
Your questions should:
1. Dig deeper into the core concern
2. Explore constraints or limitations they face
3. Understand their values and priorities
4. Reveal hidden assumptions they might have

Format: Ask the questions directly, as if speaking to them."""
            
            try:
                prime_questions = self.program_llm.analyze(
                    system_prompt="You are Prime Confident asking insightful clarifying questions.",
                    user_prompt=prime_question_prompt
                )
            except Exception as e:
                print(f"[Warning] Prime question generation failed: {e}")
                prime_questions = "Can you tell me more about your situation and what concerns you most?"
            
            print(f"[Prime]\n{prime_questions}\n")
            
            dialogue_context.append({
                "speaker": "Prime",
                "text": prime_questions,
                "type": "clarification"
            })
            
            # ===== User LLM Responds with Details =====
            print("[User Response] Thinking deeply about the situation...\n")
            
            user_response_prompt = f"""You are someone facing a decision about: "{problem_statement}"

Prime Confident just asked you these questions:
"{prime_questions}"

Respond authentically and thoughtfully:
1. Answer each question specifically and honestly
2. Share relevant details about your circumstances
3. Reveal your concerns and constraints
4. Talk about what matters to you
5. Be as realistic and human as possible

Your response:"""
            
            try:
                user_response = self.user_llm.analyze(
                    system_prompt="You are a person seeking genuine guidance. Be authentic, detailed, and honest in your responses.",
                    user_prompt=user_response_prompt
                )
            except Exception as e:
                print(f"[Warning] User response generation failed: {e}")
                user_response = "I need time to think about the implications. Can you help me consider different angles?"
            
            print(f"[You]\n{user_response}\n")
            
            dialogue_context.append({
                "speaker": "You",
                "text": user_response,
                "type": "response"
            })
            
            conversation_history.append({
                "round": clarify_turn,
                "prime_question": prime_questions[:200],
                "user_response": user_response[:200],
                "phase": "clarification"
            })
            
            self.session_manager.add_turn(
                mode="CLARIFICATION",
                user_input=user_response,
                council_positions=[],
                prime_decision=prime_questions,
                kis_items=[],
                confidence=0.5
            )
        
        print(f"\n{'-'*70}")
        print("[Prime Confident] Now I have a clear picture of your situation.\n")
        
        # ===== SYNTHESIS PHASE: System gathers knowledge and makes decision =====
        print("[Synthesis Phase] Analyzing your situation with council wisdom...\n")
        
        mode = self.session_manager.should_escalate_mode()
        print(f"[Mode] {mode}")
        
        # ===== KIS Synthesis (using full context) =====
        print("[KIS] Synthesizing knowledge from gathered details...")
        
        full_context = "\n".join([f"{entry['speaker']}: {entry['text']}" for entry in dialogue_context])
        
        kis_result = synthesize_knowledge(
            user_input=full_context,
            active_domains=domains,
            domain_confidence=domain_confidence,
            max_items=10 if mode != "QUICK" else 5
        )
        kis_items = kis_result.get("synthesized_knowledge", [])
        print(f"  ✓ Retrieved {len(kis_items)} knowledge items")
        
        # ===== Council Decision =====
        print(f"[Council] Invoking {mode} mode with full context...")
        
        try:
            council_result = self.dynamic_council.convene_for_mode(
                mode=mode,
                user_input=full_context,
                context={
                    "turn": clarification_rounds + 1,
                    "stakes": stakes,
                    "domains": domains,
                    "dialogue_depth": len(dialogue_context)
                }
            )
            council_positions = council_result.get("council_positions", []) or []
            minister_outputs = council_result.get("minister_outputs", {}) or {}
            print(f"  ✓ {len(council_positions)} ministers consulted")
        except Exception as e:
            print(f"[Warning] Council error: {e}")
            council_positions = []
            minister_outputs = {}
            council_result = {}
        
        # ===== Prime Makes Informed Decision =====
        print("[Prime Confident] Synthesizing comprehensive guidance...\n")
        
        prime_decision_prompt = f"""You are Prime Confident, the final decision authority.

Original Problem: {problem_statement}
Domains: {', '.join(domains)}
Stakes: {stakes}

Full Context from our conversation:
{full_context}

Council Inputs: {len(council_positions)} ministers have weighed in.

Now provide your final, comprehensive guidance:
1. Acknowledge what you heard from them
2. Synthesize the key tradeoffs and considerations
3. Provide clear, actionable recommendations
4. Explain your reasoning
5. State your confidence in this guidance (0-100%)

Format:
GUIDANCE: [Your main recommendation]

REASONING: [Why this makes sense for their situation]

CONFIDENCE: [Your confidence level 0-100%]"""
        
        try:
            prime_response = self.program_llm.analyze(
                system_prompt="You are Prime Confident providing wise, comprehensive guidance based on deep understanding.",
                user_prompt=prime_decision_prompt
            )
        except Exception as e:
            print(f"[Warning] Prime decision error: {e}")
            prime_response = "I recommend taking time to carefully weigh the options before making a final decision."
        
        print(f"[Prime Confident]\n{prime_response}\n")
        
        dialogue_context.append({
            "speaker": "Prime",
            "text": prime_response,
            "type": "decision"
        })
        
        final_decision = prime_response
        
        # Extract confidence from response
        final_confidence = 0.75
        if "CONFIDENCE:" in prime_response.upper():
            try:
                import re
                match = re.search(r'CONFIDENCE:?\s*(\d+)', prime_response)
                if match:
                    final_confidence = int(match.group(1)) / 100.0
            except:
                pass
        
        # ===== User LLM Feedback =====
        print("[Evaluating Guidance] How does this resonance with you?\n")
        
        user_feedback_prompt = f"""Prime Confident just gave you this guidance:

"{prime_response}"

Respond authentically:
1. How does this land for you?
2. Does it address your core concerns?
3. What additional thoughts or hesitations do you have?
4. Would you be willing to move forward with this approach?

Your honest reaction:"""
        
        try:
            user_feedback = self.user_llm.analyze(
                system_prompt="You are genuinely evaluating whether this guidance resonates with you.",
                user_prompt=user_feedback_prompt
            )
        except Exception as e:
            print(f"[Warning] User feedback failed: {e}")
            user_feedback = "This gives me a lot to think about."
        
        print(f"[You]\n{user_feedback}\n")
        
        dialogue_context.append({
            "speaker": "You",
            "text": user_feedback,
            "type": "feedback"
        })
        
        # ===== Natural Satisfaction Check =====
        print("[Satisfaction Assessment] Evaluating your satisfaction...\n")
        
        satisfaction_check_prompt = f"""Based on this conversation:

Prime's guidance: {prime_response[:300]}

User's reaction: {user_feedback[:300]}

Does the user seem satisfied, partially satisfied, or unsatisfied?
Consider: emotional tone, willingness to move forward, remaining concerns.

Respond with: SATISFIED, PARTIAL, or UNSATISFIED"""
        
        try:
            satisfaction_eval = self.user_llm.analyze(
                system_prompt="Assess whether the user is satisfied with the guidance.",
                user_prompt=satisfaction_check_prompt
            )
            
            satisfied = "SATISFIED" in satisfaction_eval.upper()
            partial = "PARTIAL" in satisfaction_eval.upper()
            
            status = "✅ SATISFIED" if satisfied else ("⚠️ PARTIAL" if partial else "❌ UNSATISFIED")
            print(f"  {status}")
        except Exception as e:
            print(f"[Warning] Satisfaction eval failed: {e}")
            satisfied = True
            status = "⚠️ PARTIAL"
        
        session_satisfied = satisfied
        
        conversation_history.append({
            "phase": "decision",
            "prime_guidance": final_decision[:300],
            "user_feedback": user_feedback[:300],
            "satisfied": satisfied
        })
        
        print(f"\n{'-'*70}")
        print("[Phase 6] Concluding session...\n")
        
        # End session with actual satisfaction from dialogue
        self.session_manager.record_satisfaction(
            satisfied=session_satisfied,
            confidence=final_confidence
        )
        
        session = self.session_manager.end_session(
            conclusion=final_decision,
            satisfaction=session_satisfied,
            confidence=final_confidence
        )
        
        final_satisfaction = session_satisfied
        
        # ===== PHASE 7: Episode & Metrics Storage =====
        print(f"[Phase 7] Storing episode and metrics...\n")
        
        self._store_episode(
            problem_statement=problem_statement,
            domains=domains,
            final_decision=final_decision,
            satisfied=final_satisfaction,
            confidence=final_confidence,
            conversation_history=conversation_history
        )
        
        self._store_metrics(
            domains=domains,
            satisfied=final_satisfaction,
            confidence=final_confidence,
            turns_used=len(dialogue_context)
        )
        
        # ===== PHASE 8: ML Analysis =====
        print(f"\n[Phase 8] Running ML analysis...\n")
        
        self._run_ml_analysis(
            domains=domains,
            decision=final_decision,
            satisfied=final_satisfaction,
            conversation_history=conversation_history
        )
        
        print(f"\n{'-'*70}")
        print("[Session Complete]")
        print(f"{'-'*70}")
        print(f"Decision: {final_satisfaction and '✅ SATISFIED' or '⚠️ PARTIAL/UNSATISFIED'}")
        print(f"Total engagement: {len(dialogue_context)} exchanges")
        print(f"Session ID: {session.get('session_id', 'unknown')}")
        print(f"Mode progression: QUICK → {self.session_manager.current_session.get('final_mode', 'QUICK')}")
        
        return {
            "problem": problem_statement,
            "domains": domains,
            "final_decision": final_decision,
            "satisfied": final_satisfaction,
            "confidence": final_confidence,
            "session_id": session.get('session_id'),
            "conversation_exchanges": len(dialogue_context)
        }
    
    # ============================================================
    # STORAGE & LEARNING
    # ============================================================
    
    def _store_episode(self, problem_statement: str, domains: list, final_decision: str, 
                       satisfied: bool, confidence: float, conversation_history: list) -> None:
        """Store session as episode for learning."""
        
        try:
            episode = Episode(
                episode_id=f"session_{self.session_count}",
                turn_id=self.total_turns,
                domain=domains[0] if domains else "general",
                user_input=problem_statement[:200],
                persona_recommendation=final_decision[:300],
                confidence=confidence,
                minister_stance="Multi-Council Synthesis",
                council_recommendation=final_decision[:300],
                outcome="success" if satisfied else "partial",
                regret_score=0.0 if satisfied else 0.5
            )
            
            self.episodic_memory.store_episode(episode)
            print("  ✓ Episode stored")
        
        except Exception as e:
            print(f"  ✗ Episode storage failed: {e}")
    
    def _store_metrics(self, domains: list, satisfied: bool, confidence: float, turns_used: int) -> None:
        """Store performance metrics."""
        
        try:
            self.performance_metrics.record_decision(
                turn=turns_used,
                domain=domains[0] if domains else "general",
                recommendation=turns_used,
                confidence=confidence,
                outcome="satisfied" if satisfied else "partial",
                regret=0.0 if satisfied else 0.5
            )
            print("  ✓ Metrics recorded")
        
        except Exception as e:
            print(f"  ✗ Metrics storage failed: {e}")
    
    def _run_ml_analysis(self, domains: list, decision: str, satisfied: bool, conversation_history: list) -> Dict[str, Any]:
        """Run ML analysis on conversation."""
        
        try:
            insights = {
                "session_number": self.session_count,
                "timestamp": datetime.now().isoformat(),
                
                "metrics": {
                    "exchanges": len(conversation_history),
                    "satisfied": satisfied,
                    "domains": domains,
                },
                
                "analysis": {
                    "domain_effectiveness": {
                        "domains_engaged": domains,
                        "resolution_success": satisfied,
                        "conversations": len(conversation_history),
                    },
                    "conversation_complexity": len(conversation_history),
                    "efficiency": {
                        "quick_resolution": len(conversation_history) <= 3,
                        "extended_dialogue": len(conversation_history) > 5
                    }
                },
                
                "learning": {
                    "success_pattern": "satisfied" if satisfied else "needs_improvement",
                    "dialogue_quality": "rich" if len(conversation_history) >= 5 else "moderate",
                    "recommendations": self._generate_ml_recommendations(satisfied, domains)
                }
            }
            
            self.learning_records.append(insights)
            self.session_history.append(insights)
            
            return insights
        
        except Exception as e:
            print(f"  ✗ ML analysis failed: {e}")
            return {}
    
    def _generate_ml_recommendations(self, satisfied: bool, domains: list) -> list:
        """Generate recommendations from ML analysis."""
        
        recommendations = []
        
        if satisfied:
            recommendations.append("✓ Back-and-forth dialogue successfully addressed user concerns")
            recommendations.append("✓ Prime's questions effectively elicited detailed user responses")
            recommendations.append("✓ Multi-turn exchange improved solution quality")
        else:
            recommendations.append("⚠ Consider deeper clarification questions in future sessions")
            recommendations.append("⚠ May need more ministerial council input for these domains")
            recommendations.append("⚠ User may benefit from exploring alternative perspectives")
        
        return recommendations
    
    # ============================================================
    # CONTINUOUS LOOP
    # ============================================================
    
    def run_continuous(self) -> None:
        """Run sessions with LLM-generated problems continuously."""
        
        print("\n" + "="*70)
        print("Decision Guidance System - Continuous Mode")
        print("\nGenerating and solving problems automatically...")
        print("Press Ctrl+C to stop\n")
        print("="*70)
        
        try:
            while True:
                result = self.run_session()
                
                if result:
                    print(f"\n[Session {self.session_count}] Complete")
                    time.sleep(1)  # Brief pause
        
        except KeyboardInterrupt:
            self._print_final_summary()
        
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    def run_interactive(self) -> None:
        """Run sessions with user-provided problems."""
        
        print("\n" + "="*70)
        print("Decision Guidance System - Manual Input Mode")
        print("="*70)
        print("\nCommands:")
        print("  [Enter] - Start new session")
        print("  stats   - Show statistics")
        print("  exit    - Exit program\n")
        
        try:
            while True:
                try:
                    cmd = input("[Menu] > ").strip().lower()
                    
                    if cmd == "exit":
                        print("\n[Done] Goodbye")
                        break
                    elif cmd == "stats":
                        self._print_summary_stats()
                    elif cmd == "":
                        self.run_session()
                    else:
                        self.run_session(problem_statement=cmd)
                
                except EOFError:
                    break
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self._print_final_summary()
    
    def _print_summary_stats(self) -> None:
        """Print session summary statistics."""
        
        if self.session_count == 0:
            print("\n[Info] No sessions completed yet")
            return
        
        satisfied_count = len([r for r in self.learning_records if r.get("metrics", {}).get("satisfied")])
        avg_turns = self.total_turns / self.session_count if self.session_count > 0 else 0
        
        print("\n" + "="*70)
        print("SESSION STATISTICS")
        print("="*70)
        print(f"Total sessions: {self.session_count}")
        print(f"Total turns: {self.total_turns}")
        print(f"Average turns/session: {avg_turns:.1f}")
        print(f"Satisfied: {satisfied_count}/{self.session_count} ({100*satisfied_count/self.session_count:.0f}%)")
        print(f"Learning records: {len(self.learning_records)}")
        print("="*70 + "\n")
    
    def _print_final_summary(self) -> None:
        """Print final summary on exit."""
        
        print("\n" + "="*70)
        print("🏁 SESSION SUMMARY")
        print("="*70)
        
        print(f"\nSessions completed: {self.session_count}")
        print(f"Total turns: {self.total_turns}")
        print(f"Avg turns/session: {self.total_turns/self.session_count:.1f}" if self.session_count > 0 else "N/A")
        
        if self.learning_records:
            satisfied = len([r for r in self.learning_records if r.get("metrics", {}).get("satisfied")])
            print(f"Satisfaction rate: {satisfied}/{self.session_count} ({100*satisfied/self.session_count:.0f}%)")
        
        print("\n[Data Location]")
        print("  → data/sessions/completed/")
        print("  → data/memory/episodes.jsonl")
        print("  → data/memory/metrics.jsonl")
        print("  → data/conversations/")
        
        print("\n" + "="*70 + "\n")


# ============================================================
# MAIN
# ============================================================

def main():
    """Entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Decision Guidance System")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto",
                        help="auto=LLM-generated problems, manual=user-provided problems")
    parser.add_argument("--verbose", action="store_true", default=True)
    
    args = parser.parse_args()
    
    system = DecisionGuidanceSystem(
        auto_generate=(args.mode == "auto"),
        verbose=args.verbose
    )
    
    if args.mode == "auto":
        system.run_continuous()
    else:
        system.run_interactive()


if __name__ == "__main__":
    main()
