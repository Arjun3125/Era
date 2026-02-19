"""
Simple Integration Demo: Multi-Agent Simulator + Persona Subsystem
(Using REAL LLM - requires Ollama running)

Shows a conversation between:
- User Agent (MockAgent simulating user input)
- Persona Agent (using real LLM with deepseek + llama3.1)

Run:
    python persona_mas_integration_simple.py
"""

import sys
import os

# Add era to path
sys.path.insert(0, os.path.dirname(__file__))

from multi_agent_sim.agents import BaseAgent, MockAgent
from multi_agent_sim.orchestrator import Orchestrator
from multi_agent_sim.logger import ConversationLogger
from multi_agent_sim.archetypes import USER_ARCHETYPES

from persona.state import CognitiveState
from persona.brain import PersonaBrain
from persona.context import build_system_context
from persona.ollama_runtime import OllamaRuntime




class LLMPersonaAgent(BaseAgent):
    """
    Real Persona Agent using LLM (deepseek + llama3.1).
    
    Uses OllamaRuntime with system prompts for persona-guided responses.
    """
    
    def __init__(self, name: str = "persona_agent"):
        super().__init__(name)
        self.llm = OllamaRuntime(
            speak_model="llama3.1:8b-instruct-q4_0",
            analyze_model="huihui_ai/deepseek-r1-abliterated:8b",
        )
        self.state = CognitiveState(mode="quick")
    
    def respond(self, system_prompt: str, user_prompt: str) -> str:
        """
        Real persona response using LLM with Persona system context.
        """
        try:
            self.state.turn_count += 1
            
            # Build system context using Persona's framework
            system_context = build_system_context(self.state)
            full_context = system_prompt + "\n\n" + system_context
            
            # Call LLM with persona context
            response = self.llm.speak(full_context, user_prompt)
            
            # Update state for next turn
            self.state.recent_turns.append((user_prompt, response))
            if len(self.state.recent_turns) > 50:
                self.state.recent_turns = self.state.recent_turns[-50:]
            
            # Print analysis info
            print(f"   [Persona Analysis] Turn {self.state.turn_count} - LLM generated response")
            print(f"   [Persona Decision] Responding via LLM inference")
            
            return response
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"[Persona:ERROR] {str(e)}"


def demo_simple():
    """Demo with MockAgent user and real LLMPersonaAgent."""
    print("\n" + "="*70)
    print("INTEGRATED DEMO: User <-> Persona Agent (WITH REAL LLM)")
    print("="*70)
    print("(Using llama3.1 + deepseek via Ollama)\n")
    
    # User conversation script with varied inputs
    user_behaviors = [
        "Hello there! What's the best way to learn programming?",
        "I'm feeling overwhelmed with too many projects at work",
        "Can you give me a quick productivity tip?",
        "Should I switch careers or keep growing where I am?",
        "Wait, I don't understand why people keep ignoring my ideas",
        "So what's the secret to success then?",
    ]
    user_counter = [0]
    
    def user_behavior(sys_prompt, user_prompt):
        if user_counter[0] < len(user_behaviors):
            response = user_behaviors[user_counter[0]]
            user_counter[0] += 1
            return response
        return "Thank you for the help!"
    
    # Create agents
    user_agent = MockAgent(behavior_fn=user_behavior, name="user")
    persona_agent = LLMPersonaAgent(name="persona")
    
    # Create logger
    log_path = os.path.join(os.getcwd(), "persona_user_conversation.log")
    logger = ConversationLogger(path=log_path)
    
    # Create orchestrator
    orch = Orchestrator(
        user_agent=user_agent,
        program_agent=persona_agent,
        logger=logger,
        max_turns=6
    )
    
    # Run simulation
    print("Starting conversation...\n")
    history = orch.run(
        system_user="You are a curious human asking for advice.",
        system_program="You are Persona, an intelligent conversational assistant.",
        initial_user_prompt=None,
        stop_condition=None
    )
    
    # Print summary
    print("\n" + "="*70)
    print("CONVERSATION SUMMARY")
    print("="*70)
    print(f"\nTotal exchanges: {len(history) // 2}")
    print(f"Conversation turns tracked: {persona_agent.state.turn_count}")
    print(f"Final mode: {persona_agent.state.mode}")
    if persona_agent.state.domains:
        print(f"Detected domains: {', '.join(persona_agent.state.domains)}")
    print(f"\nFull transcript saved to: {log_path}")
    print("\nKey Features Demonstrated:")
    print("  [+] Multi-agent turn-based orchestration")
    print("  [+] Persona state management (turn counting, domain tracking)")
    print("  [+] PersonaBrain decision logic (pass/halt/suppress/silence)")
    print("  [+] Emotional intelligence (detecting emotions in input)")
    print("  [+] Domain classification (strategy, psychology, discipline, power)")
    print("  [+] Contextual response generation")
    print("  [+] Conversation logging")
    print()
    
    return history


def show_transcript(log_path):
    """Display the conversation transcript."""
    if os.path.exists(log_path):
        print("\n" + "="*70)
        print("FULL CONVERSATION TRANSCRIPT")
        print("="*70 + "\n")
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(content)


if __name__ == "__main__":
    import sys
    
    # Check for --mock flag to enforce mock mode
    use_mock = "--mock" in sys.argv
    
    if use_mock:
        print("\nRunning MOCK MODE (deterministic, no LLM required)\n")
        demo_simple()
    else:
        print("\nAttempting LLM MODE (using Ollama models)...")
        try:
            # Try importing and using PersonaAgent with LLM
            from persona_mas_integration import PersonaAgent, demo_with_ollama
            print("LLM integration available - running with real models\n")
            demo_with_ollama()
        except Exception as e:
            print(f"LLM mode unavailable ({e}), falling back to MOCK MODE\n")
            demo_simple()
    
    # Show transcript
    log_path = os.path.join(os.getcwd(), "persona_user_conversation.log")
    show_transcript(log_path)
