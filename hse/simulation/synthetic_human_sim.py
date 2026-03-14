# hse/simulation/synthetic_human_sim.py
"""
Synthetic Human Simulation: Generates realistic human responses to Persona advice.
Creates bidirectional conversation loop for stress testing.
"""

from typing import Optional, Dict, Any, List, Tuple
from hse.human_profile import SyntheticHuman
from hse.crisis_injector import CrisisInjector
from hse.personality_drift import PersonalityDrift

class SyntheticHumanSimulation:
    def __init__(self, human: SyntheticHuman, user_llm=None):
        """
        Initialize synthetic human for long-horizon testing.
        
        Args:
            human: SyntheticHuman instance (persistent across turns)
            user_llm: LLM for generating realistic human responses
        """
        self.human = human
        self.user_llm = user_llm
        self.crisis_injector = CrisisInjector(seed=human.seed)
        self.personality_drift = PersonalityDrift(seed=human.seed)
        self.human_history: List[Tuple[int, str]] = []  # (turn, input)
        self.turn = 0
    
    def generate_next_input(self, persona_response: str, context: Dict[str, Any] = None) -> str:
        """
        Generate realistic human input based on:
        - Previous human state
        - Persona's response (did it help?)
        - Unresolved issues
        - Current crisis state
        """
        import sys
        import threading
        import queue
        
        self.turn += 1
        
        # Build context for human LLM
        recent_history = self.human_history[-3:] if self.human_history else []
        unresolved = self.human.get("unresolved_issues", [])
        
        system_prompt = """You are a helpful response generator for a synthetic human character. 
Keep responses natural, 2-3 sentences, conversational tone. The human should respond realistically based on their situation."""
        
        user_prompt = f"""You are {self.human.name}, a synthetic human navigating real-life challenges.

Recent state:
- Age: {self.human.get('age', 30)}
- Profession: {self.human.get('profession', 'unknown')}
- Wealth: {self.human.get('wealth', 'unstable')}
- Unresolved issues: {unresolved}
- Personality traits: {self.human.get('traits', {})}

You just received this advice from an advisor:
{persona_response}

Respond naturally as this human would. Consider:
- Do you trust this advisor?
- Does this advice feel practical?
- What concerns do you have?
- What's your next move?

Respond in 2-3 sentences."""
        
        response = None
        if self.user_llm:
            try:
                print(f"[LLMCALL] Calling user LLM for synthetic response (turn {self.turn}, timeout 30s)...", file=sys.stderr, flush=True)
                sys.stderr.flush()
                
                # Call LLM with timeout using threading
                result_queue = queue.Queue()
                
                def call_llm():
                    try:
                        # Use analyze() instead of speak() to avoid mixing conversation histories
                        result = self.user_llm.analyze(system_prompt, user_prompt)
                        result_queue.put(("success", result))
                    except Exception as e:
                        result_queue.put(("error", e))
                
                thread = threading.Thread(target=call_llm, daemon=True)
                thread.start()
                thread.join(timeout=30)  # Wait max 30 seconds
                
                if thread.is_alive():
                    print(f"[LLMERROR] LLM call timed out after 30s", file=sys.stderr, flush=True)
                    response = "I need more time to think about that."
                else:
                    try:
                        status, result = result_queue.get_nowait()
                        if status == "success":
                            print(f"[LLMDONE] User LLM returned: {len(result)} chars", file=sys.stderr, flush=True)
                            response = result
                        else:
                            print(f"[LLMERROR] LLM call failed: {type(result).__name__}: {result}", file=sys.stderr, flush=True)
                            response = f"I need to think about that."
                    except queue.Empty:
                        print(f"[LLMERROR] LLM thread completed but no result", file=sys.stderr, flush=True)
                        response = "That's an interesting perspective."
                        
            except Exception as e:
                print(f"[LLMERROR] LLM setup failed: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                response = "I need to think about that."
        else:
            response = "That's helpful, but I'm still uncertain about my next steps."
        
        if not response:
            response = "That's an interesting perspective. Let me consider that more."
            
        self.human_history.append((self.turn, response))
        return response
    
    def apply_consequences(self, decision_quality: float, domain: str = "general") -> Dict[str, Any]:
        """
        Propagate consequences of Persona's advice on human's life.
        Returns outcome metrics.
        """
        outcome = "success" if decision_quality > 0.6 else "failure"
        regret = 1.0 - decision_quality
        
        # Apply wealth/health/relationship changes
        if domain == "career":
            if outcome == "success":
                self.human["wealth"] = "improved_income"
            else:
                self.human["wealth"] = "lost_opportunity"
        
        elif domain == "health":
            if outcome == "success":
                self.human["health"] = "improving"
            else:
                self.human["health"] = "declined"
        
        elif domain == "relationships":
            if outcome == "success":
                self.human["relationships"] = "strengthened"
            else:
                self.human["relationships"] = "strained"
        
        # Drift personality based on outcome
        signals = {
            "stress": 0.8 if outcome == "failure" else 0.3,
            "success_rate": 0.8 if outcome == "success" else 0.2,
            "repetition": 0.5
        }
        drift_record = self.personality_drift.apply(self.human, signals)
        
        # Possibly inject crisis
        crisis = self.crisis_injector.maybe_inject(self.human.get("id", "unknown"), self.human, self.turn)
        
        return {
            "outcome": outcome,
            "regret_score": regret,
            "domain": domain,
            "crisis_injected": crisis is not None
        }
