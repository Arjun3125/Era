"""
Session-Based Conversation Runner

Implements the full workflow:
1. User provides problem statement
2. Domain detection auto-sets active domains
3. Multi-turn conversation with mode escalation (QUICK -> MEETING -> WAR -> DARBAR)
4. KIS synthesis, council decision, prime confident conclusion
5. Satisfaction checking
6. Session storage with consequences tracking
7. Problem continuity (follow-ups, related sessions)
8. New session starts automatically
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Optional, List
from persona.domain_detector import analyze_situation, domain_similarity
from persona.session_manager import SessionManager
from persona.modes.mode_orchestrator import ModeOrchestrator
from persona.knowledge_engine import synthesize_knowledge
from persona.council.dynamic_council import DynamicCouncil
from sovereign.prime_confident import PrimeConfident
from persona.learning.episodic_memory import EpisodicMemory
from persona.learning.performance_metrics import PerformanceMetrics
from llm.ollama import OllamaRuntime
from hse.simulation.synthetic_human_sim import SyntheticHumanSimulation


class SessionBasedConversation:
    """Orchestrates multi-turn problem-solving sessions with all features."""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.mode_orchestrator = ModeOrchestrator()
        self.dynamic_council = DynamicCouncil()
        self.prime_confident = PrimeConfident()
        self.episodic_memory = EpisodicMemory(storage_path="data/memory/episodes.jsonl")
        self.metrics = PerformanceMetrics(storage_path="data/memory/metrics.jsonl")
        
        # Initialize LLM for user simulation
        try:
            self.user_llm = OllamaRuntime(
                model_name="llama3.1:8b-instruct-q4_0",
                base_url="http://localhost:11434"
            )
        except Exception as e:
            print(f"[Warning] Could not initialize user LLM: {e}")
            self.user_llm = None
        
        # Synthetic human for automated testing
        self.synthetic_human = SyntheticHumanSimulation(self.user_llm) if self.user_llm else None
        
        # Program LLM (Persona N)
        try:
            self.program_llm = OllamaRuntime(
                model_name="qwen3:14b",
                base_url="http://localhost:11434"
            )
        except Exception as e:
            print(f"[Warning] Could not initialize program LLM: {e}")
            self.program_llm = None
    
    def run_session(self, initial_problem: Optional[str] = None):
        """
        Run a complete problem-solving session.
        
        Flow:
        1. Get problem statement
        2. Auto-detect domains
        3. Check for related previous sessions
        4. Loop: turn -> mode escalation -> council -> prime decision -> satisfaction check
        5. End session and store
        """
        # ===== PHASE 1: Problem Intake =====
        if initial_problem is None:
            problem_statement = input("\n🎯 What's your problem or concern? (or type 'exit' to quit)\n>> ").strip()
            
            if problem_statement.lower() == "exit":
                return
        else:
            problem_statement = initial_problem
        
        if not problem_statement:
            print("[Error] Problem statement cannot be empty")
            return
        
        # ===== PHASE 2: Domain Detection =====
        print("\n[Analysis] Analyzing problem statement...")
        analysis = analyze_situation(problem_statement, llm_adapter=self.program_llm)
        
        domains = analysis["domains"]
        domain_confidence = analysis["domain_confidence"]
        stakes = analysis["stakes"]
        reversibility = analysis["reversibility"]
        
        print(f"↳ Detected domains: {', '.join(domains) if domains else 'general'}")
        print(f"↳ Stakes: {stakes} | Reversibility: {reversibility}")
        
        # ===== PHASE 3: Session Continuity Check =====
        relevant_sessions = self.session_manager.find_related_sessions(domains, limit=2)
        if relevant_sessions:
            print("\n[Memory] Found related previous sessions:")
            for prev_session in relevant_sessions:
                print(f"  • {prev_session.problem_statement[:60]}... → {prev_session.final_conclusion[:40]}...")
        
        # ===== PHASE 4: Start Session =====
        session = self.session_manager.start_session(
            problem_statement=problem_statement,
            domains=domains if domains else ["strategy"],
            domain_confidence=domain_confidence,
            stakes=stakes,
            reversibility=reversibility,
            parent_session_id=relevant_sessions[0].session_id if relevant_sessions else None
        )
        
        # ===== PHASE 5: Multi-Turn Loop =====
        session_satisfied = False
        
        for turn_num in range(1, 11):  # Max 10 turns per session
            print(f"\n{'='*60}")
            print(f"TURN {turn_num}")
            print('='*60)
            
            # Auto-escalate mode based on turn count
            mode = self.session_manager.should_escalate_mode()
            print(f"[Mode] {mode}")
            
            # ===== KIS Synthesis =====
            print(f"[KIS] Synthesizing knowledge...")
            kis_result = synthesize_knowledge(
                user_input=problem_statement,
                active_domains=session.domains,
                domain_confidence=domain_confidence,
                max_items=5 if mode == "QUICK" else 10
            )
            kis_items = kis_result.get("synthesized_knowledge", [])
            print(f"↳ Retrieved {len(kis_items)} knowledge items")
            
            # ===== Council Decision =====
            print(f"[Council] Invoking {mode} mode...")
            try:
                council_rec = self.dynamic_council.invoke(
                    user_input=problem_statement,
                    mode=mode,
                    domain=session.domains[0] if session.domains else "strategy",
                    context={"turn": turn_num, "stakes": stakes}
                )
                council_positions = council_rec.get("council_positions", [])
                print(f"↳ {len(council_positions)} ministers consulted")
            except Exception as e:
                print(f"[Warning] Council error: {e}")
                council_positions = []
            
            # ===== Prime Confident Decision =====
            print(f"[Prime] Synthesizing final decision...")
            try:
                final_decision = self.prime_confident.decide(
                    council_rec=council_rec if council_positions else {},
                    user_input=problem_statement
                )
                decision_text = final_decision.get("decision", "No clear recommendation at this time")
                confidence = final_decision.get("confidence", 0.5)
            except Exception as e:
                print(f"[Warning] Prime decision error: {e}")
                decision_text = "Unable to generate decision"
                confidence = 0.3
            
            print(f"\n[Decision]\n{decision_text}\n")
            print(f"Confidence: {confidence:.2f}")
            
            # ===== Record Turn =====
            self.session_manager.add_turn(
                mode=mode,
                user_input=problem_statement,
                council_positions=council_positions,
                prime_decision=decision_text,
                kis_items=kis_items,
                confidence=confidence
            )
            
            # ===== Satisfaction Check & Iteration =====
            if self.synthetic_human:
                # Automated: synthetic human evaluates decision
                satisfaction_eval = self.synthetic_human.evaluate_decision(
                    decision=decision_text,
                    problem=problem_statement,
                    mode=mode
                )
                user_satisfied = satisfaction_eval.get("satisfied", False)
                satisfaction_confidence = satisfaction_eval.get("confidence", 0.5)
                
                print(f"\n[Feedback] User satisfaction: {user_satisfied} ({satisfaction_confidence:.2f})")
            else:
                # Manual: ask user
                user_response = input("\nDoes this address your concern? (yes/no/maybe): ").strip().lower()
                user_satisfied = user_response == "yes"
                satisfaction_confidence = 0.9 if user_satisfied else (0.5 if user_response == "maybe" else 0.1)
            
            self.session_manager.record_satisfaction(
                satisfied=user_satisfied,
                confidence=satisfaction_confidence
            )
            
            # Check if we should continue or end
            should_continue = self.session_manager.record_satisfaction(
                satisfied=user_satisfied,
                confidence=satisfaction_confidence
            )
            
            if not should_continue or user_satisfied:
                session_satisfied = user_satisfied
                break
        
        # ===== PHASE 6: Session Conclusion =====
        conclusion = self._generate_conclusion(session, decision_text, user_satisfied)
        
        session = self.session_manager.end_session(
            conclusion=conclusion,
            satisfaction=session_satisfied,
            confidence=confidence
        )
        
        # ===== PHASE 7: Store in Memory =====
        self._store_session_episode(session)
        
        # ===== PHASE 8: Follow-up Option =====
        print("\n" + "="*60)
        print("SESSION COMPLETE")
        print("="*60)
        
        if self.synthetic_human:
            # Auto-loop for simulation
            self.run_session()
        else:
            # Ask if user wants follow-up
            followup = input("\nWould you like to discuss a follow-up or related problem? (yes/no): ").strip().lower()
            if followup == "yes":
                if relevant_sessions:
                    print(f"\n[Continuity] Your new problem will be linked to this session (#{session.session_id[-8:]})")
                self.run_session()
    
    def _generate_conclusion(self, session, last_decision: str, satisfied: bool) -> str:
        """Generate a comprehensive session conclusion"""
        conclusions = [
            f"Decision: {last_decision[:100]}",
            f"Domains addressed: {', '.join(session.domains)}",
            f"Decision reached after {len(session.turns)} turn(s) of analysis",
            f"Overall confidence: {session.turns[-1].confidence if session.turns else 0:.2f}",
        ]
        
        if satisfied:
            conclusions.append("User expressed satisfaction with the decision.")
        else:
            conclusions.append("Further discussion may be needed to fully resolve the concern.")
        
        return " | ".join(conclusions)
    
    def _store_session_episode(self, session):
        """Store session as an episode in episodic memory"""
        try:
            episode = {
                "session_id": session.session_id,
                "problem": session.problem_statement[:100],
                "domains": session.domains,
                "stakes": session.stakes,
                "turns": len(session.turns),
                "conclusion": session.final_conclusion[:100] if session.final_conclusion else "",
                "satisfied": session.final_satisfaction,
                "confidence": session.final_confidence
            }
            
            self.episodic_memory.store_episode(
                user_input=session.problem_statement,
                recommendation=session.final_conclusion or "Inconclusive",
                confidence=session.final_confidence or 0.5,
                outcome="satisfied" if session.final_satisfaction else "inconclusive"
            )
            
            # Store metrics
            self.metrics.record_metric(
                decision_text=session.final_conclusion or "Inconclusive",
                confidence=session.final_confidence or 0.5,
                mode=session.turns[-1].mode if session.turns else "QUICK",
                outcome="success" if session.final_satisfaction else "tentative"
            )
        except Exception as e:
            print(f"[Warning] Could not store session episode: {e}")
    
    def show_statistics(self):
        """Display session statistics"""
        stats = self.session_manager.get_session_statistics()
        
        print("\n" + "="*60)
        print("SESSION STATISTICS")
        print("="*60)
        print(f"Total sessions: {stats['total_sessions']}")
        print(f"Average turns per session: {stats['avg_turns']:.1f}")
        print(f"User satisfaction rate: {stats['satisfaction_rate']:.1%}")
        print(f"Most common domains: {', '.join(stats['most_common_domains'])}")
        print(f"Average confidence: {stats['avg_confidence']:.2f}")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("PERSONA N - SESSION-BASED PROBLEM SOLVING")
    print("="*60)
    print("\nSession-based workflow:")
    print("1. You describe your problem or life concern")
    print("2. System auto-detects relevant domains")
    print("3. Multi-turn conversation with smart mode escalation")
    print("4. KIS synthesis, Council decision, Prime authority conclusion")
    print("5. Satisfaction checking & session storage")
    print("6. Problem continuity (follow-ups, related sessions)")
    print("\nType 'exit' to quit, 'stats' for session statistics\n")
    
    conversation = SessionBasedConversation()
    
    while True:
        try:
            # Alternative: accept command
            cmd = input("\n[Menu] Start session > ").strip().lower()
            
            if cmd == "exit":
                print("\n✓ Goodbye")
                break
            elif cmd == "stats":
                conversation.show_statistics()
            elif cmd == "":
                conversation.run_session()
            else:
                # Treat as problem statement
                conversation.run_session(initial_problem=cmd)
        except KeyboardInterrupt:
            print("\n✓ Session interrupted")
            break
        except Exception as e:
            print(f"[Error] {e}")


if __name__ == "__main__":
    main()
