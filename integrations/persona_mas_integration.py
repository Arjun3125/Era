"""
Integration demo: Multi-Agent Simulator + Persona Subsystem

Shows a conversation between:
- User Agent (MockAgent simulating user input)
- Persona Agent (using persona logic with PersonaBrain control)

Run:
    python -m era_mas_persona_demo
    
or:
    python persona_mas_integration.py
"""

import sys
import os

# Add era to path
sys.path.insert(0, os.path.dirname(__file__))

from multi_agent_sim.agents import BaseAgent, MockAgent
from multi_agent_sim.orchestrator import Orchestrator
from multi_agent_sim.logger import ConversationLogger
from multi_agent_sim.archetypes import USER_ARCHETYPES, PROGRAM_SYSTEM

from persona.state import CognitiveState
from persona.brain import PersonaBrain
from persona.analysis import (
    assess_situation,
    assess_coherence,
    classify_domains,
    assess_emotional_metrics,
)
from persona.context import build_system_context
from persona.ollama_runtime import OllamaRuntime
from persona.clarify import build_clarifying_question, format_question_for_user


class PersonaAgent(BaseAgent):
    """
    Wraps the Persona subsystem as an agent for multi-agent simulation.
    
    Uses:
    - OllamaRuntime for LLM calls
    - PersonaBrain for decision logic
    - CognitiveState for conversation memory
    - analysis.py functions for understanding
    """
    
    def __init__(self, name: str = "persona_agent", speak_model: str = None, analyze_model: str = None):
        super().__init__(name)
        # Use best available models by default:
        # - analyze_model: deepseek for superior reasoning & doctrine analysis
        # - speak_model: llama3.1 for natural, contextual dialogue
        self.llm = OllamaRuntime(
            speak_model=speak_model or "llama3.1:8b-instruct-q4_0",
            analyze_model=analyze_model or "huihui_ai/deepseek-r1-abliterated:8b"
        )
        self.brain = PersonaBrain()
        self.state = CognitiveState(mode="quick")
    
    def respond(self, system_prompt: str, user_prompt: str) -> str:
        """
        Persona response logic:
        1. Parse user input
        2. Run background analysis (situation, coherence, domains, emotions)
        3. Use PersonaBrain to decide action (pass/halt/suppress/silence)
        4. Generate response or ask clarification
        """
        try:
            # Track turn
            self.state.turn_count += 1
            
            # Quick coherence check
            coherence_result = assess_coherence(self.llm, user_prompt)
            coherence = coherence_result.get("coherence", 0.5)
            intent_present = coherence_result.get("intent_present", True)
            
            if not intent_present or coherence < 0.3:
                return f"[Persona] I don't understand that input. Could you rephrase?"
            
            # Situation assessment (what's the user really trying to do?)
            situation = assess_situation(self.llm, user_prompt)
            self.state.last_situation = situation
            
            # Emotional metrics
            emotional = assess_emotional_metrics(self.llm, user_prompt)
            self.state.emotional_metrics = emotional
            
            # Domain classification
            domains_result = classify_domains(self.llm, user_prompt, force_guess=False)
            if domains_result.get("domains"):
                self.state.domains = domains_result["domains"]
                self.state.domain_confidence = float(domains_result.get("confidence", 0.0))
            
            # PersonaBrain decides what to do
            directive = self.brain.decide(
                coherence={"coherence": coherence},
                situation=situation,
                state=self.state.__dict__
            )
            
            # Handle directive
            if directive.status == "silence" or directive.action == "block":
                return f"[Persona:SILENT] (clarity too low for casual chat)"
            
            elif directive.status == "halt" or directive.action == "ask":
                # Ask clarifying question
                clarify_q = build_clarifying_question(directive, self.state)
                return f"[Persona:CLARIFY] {clarify_q}"
            
            elif directive.status == "suppress" or directive.action == "suppress":
                # Acknowledge but suggest pause
                return f"[Persona:SUPPRESS] I sense some emotion here. Maybe take a break and come back to this?"
            
            elif directive.status == "pass" or directive.action == "speak":
                # Generate full response
                system_context = build_system_context(self.state)
                response = self.llm.speak(system_context, user_prompt)
                
                # Store turn in history
                self.state.recent_turns.append((user_prompt, response))
                if len(self.state.recent_turns) > 10:
                    self.state.recent_turns = self.state.recent_turns[-10:]
                
                return response
            
            else:
                # Default: speak
                system_context = build_system_context(self.state)
                response = self.llm.speak(system_context, user_prompt)
                self.state.recent_turns.append((user_prompt, response))
                return response
        
        except Exception as e:
            return f"[Persona:ERROR] {str(e)}"


def demo_with_mocks():
    """Demo with MockAgent user and PersonaAgent as system."""
    print("\n" + "="*70)
    print("MULTI-AGENT SIMULATION: MockUser <-> PersonaAgent")
    print("="*70 + "\n")
    
    # Create agents
    user_behaviors = [
        "What's the best way to learn programming?",
        "I'm feeling overwhelmed with too many projects",
        "Can you give me a quick tip for productivity?",
        "I don't understand why my code is broken",
        "Should I switch careers?",
    ]
    user_counter = [0]
    
    def user_behavior(sys_prompt, user_prompt):
        if user_counter[0] < len(user_behaviors):
            response = user_behaviors[user_counter[0]]
            user_counter[0] += 1
            return response
        return f"Thanks for the help!"
    
    user_agent = MockAgent(behavior_fn=user_behavior, name="user")
    persona_agent = PersonaAgent(name="persona")
    
    # Create logger
    log_path = os.path.join(os.getcwd(), "persona_mas_conversation.log")
    logger = ConversationLogger(path=log_path)
    
    # Create orchestrator
    orch = Orchestrator(
        user_agent=user_agent,
        program_agent=persona_agent,
        logger=logger,
        max_turns=6
    )
    
    # Run simulation
    history = orch.run(
        system_user=USER_ARCHETYPES["curious"],
        system_program="You are Persona, an intelligent conversational assistant.",
        initial_user_prompt=None,
        stop_condition=None
    )
    
    # Print summary
    print("\n" + "="*70)
    print("CONVERSATION SUMMARY")
    print("="*70 + "\n")
    print(f"Total exchanges: {len(history) // 2}")
    print(f"User domains detected: {persona_agent.state.domains}")
    print(f"Final mode: {persona_agent.state.mode}")
    print(f"Log saved to: {log_path}")
    print()
    
    return history


def demo_with_ollama():
    """Demo with OllamaAgent user and PersonaAgent as system."""
    from multi_agent_sim.agents import OllamaAgent
    
    print("\n" + "="*70)
    print("MULTI-AGENT SIMULATION: OllamaUser <-> PersonaAgent (LIVE)")
    print("="*70)
    print("\nNote: This requires Ollama running with at least mistral model\n")
    
    # Create agents
    user_agent = OllamaAgent(model="mistral:7b", name="user", timeout=60)
    persona_agent = PersonaAgent(name="persona")
    
    # Create logger
    log_path = os.path.join(os.getcwd(), "persona_mas_live_conversation.log")
    logger = ConversationLogger(path=log_path)
    
    # Create orchestrator
    orch = Orchestrator(
        user_agent=user_agent,
        program_agent=persona_agent,
        logger=logger,
        max_turns=5
    )
    
    # Run simulation
    history = orch.run(
        system_user=USER_ARCHETYPES["curious"],
        system_program="You are Persona, an intelligent conversational assistant.",
        initial_user_prompt="Hi there, I need some advice on time management",
        stop_condition=None
    )
    
    # Print summary
    print("\n" + "="*70)
    print("LIVE CONVERSATION SUMMARY")
    print("="*70 + "\n")
    print(f"Total exchanges: {len(history) // 2}")
    print(f"User domains: {persona_agent.state.domains}")
    print(f"Final mode: {persona_agent.state.mode}")
    print(f"Conversations turns: {persona_agent.state.turn_count}")
    print(f"Log saved to: {log_path}")
    print()
    
    return history


if __name__ == "__main__":
    import sys
    
    # Check for --mock flag to use mock mode (default is now LLM-based)
    use_mock = "--mock" in sys.argv
    
    if use_mock:
        print("\nRunning MOCK MODE (deterministic, no LLM required)")
        print("For LLM mode with Ollama, run: python persona_mas_integration.py\n")
        demo_with_mocks()
    else:
        print("\nRunning LLM MODE (using Ollama models)")
        print("For mock mode without LLM, use: python persona_mas_integration.py --mock\n")
        try:
            demo_with_ollama()
        except Exception as e:
            print(f"Error in LLM mode: {e}")
            print("\nFalling back to mock mode...")
            demo_with_mocks()
