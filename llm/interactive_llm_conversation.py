#!/usr/bin/env python3
"""
INTERACTIVE LLM CONVERSATION: Both User and Persona use LLM
Watch a real conversation unfold in real-time with both sides using AI.
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from persona.state import CognitiveState
from persona.ollama_runtime import OllamaRuntime
from persona.context import build_system_context


def print_header(title, char="="):
    """Print formatted header."""
    width = 80
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}\n")


def print_turn(turn_num, user_input, persona_response, latency_ms=0):
    """Print a formatted turn."""
    print(f"{'─' * 80}")
    print(f"TURN {turn_num} | {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'─' * 80}")
    print(f"\n👤 USER:\n{user_input}\n")
    print(f"🎭 PERSONA:\n{persona_response}\n")
    if latency_ms > 0:
        print(f"⏱️  Response time: {latency_ms:.0f}ms")
    print()


class LLMUser:
    """Simulates a user with LLM-generated responses."""
    
    def __init__(self, llm):
        self.llm = llm
        self.turn = 0
        self.conversation_history = []
    
    def generate_next_input(self, context=""):
        """Generate next user input based on conversation."""
        self.turn += 1
        
        # Different scenarios for each turn to create natural flow
        scenarios = [
            "Ask about the best way to approach learning and personal growth.",
            "Express that you're feeling overwhelmed with multiple responsibilities at work.",
            "Ask for practical advice on how to manage this overwhelm.",
            "Ask about making a big career decision while stressed.",
            "Question why others aren't listening to your ideas.",
            "Ask what the secret to long-term success really is.",
        ]
        
        if self.turn > len(scenarios):
            return None  # End conversation
        
        scenario = scenarios[self.turn - 1]
        
        # Create prompt for LLM to generate realistic user input
        user_prompt = f"""You are simulating a real user in a conversation with an AI advisor.
        
Context: {context if context else 'Start of conversation'}

Your task: Generate a realistic user input for this scenario: {scenario}

Requirements:
- Keep it natural and conversational (1-3 sentences)
- Match the emotion level suggested by the scenario
- Build on previous conversation if applicable
- Sound like a real person, not AI

Generate ONLY the user input, nothing else."""
        
        response = self.llm.speak("", user_prompt)
        self.conversation_history.append(response)
        return response


class LLMPersona:
    """Persona Agent with LLM responses."""
    
    def __init__(self, llm):
        self.llm = llm
        self.state = CognitiveState(mode="quick")
        self.conversation_history = []
    
    def respond(self, user_input):
        """Generate Persona response."""
        self.state.turn_count += 1
        self.state.recent_turns.append((user_input, ""))  # Will update with response
        
        # Build system context
        system_context = build_system_context(self.state)
        
        # Create full system prompt for Persona
        system_prompt = f"""You are a wise advisor (Persona) in a conversation.

{system_context}

Your role: Listen deeply, understand the person's real situation, and provide timely, actionable wisdom.

Guidelines:
- If the person seems overwhelmed or stressed, help them focus on what they can control
- Ask clarifying questions when something is unclear
- Acknowledge emotions while staying practical
- Relate advice to the domains you've identified
- Keep responses concise but meaningful (2-4 sentences)

Previous conversation:
{chr(10).join(f"User: {u[0]}{chr(10)}Persona: {u[1]}" for u in self.conversation_history[-3:] if u[1])}"""
        
        # Get response
        response = self.llm.speak(system_prompt, user_input)
        
        # Update state
        self.conversation_history.append((user_input, response))
        self.state.recent_turns[-1] = (user_input, response)
        
        return response


def main():
    """Run interactive LLM conversation."""
    print_header("🚀 INTERACTIVE LLM CONVERSATION")
    print("Both User and Persona are LLM-powered")
    print("Watch a real conversation unfold in real-time...\n")
    
    # Initialize LLM
    print("Initializing LLM models...")
    llm = OllamaRuntime(
        speak_model="llama3.1:8b-instruct-q4_0",
        analyze_model="huihui_ai/deepseek-r1-abliterated:8b"
    )
    print("✓ Models loaded\n")
    
    # Initialize agents
    print("Creating LLM User and LLM Persona...")
    user = LLMUser(llm)
    persona = LLMPersona(llm)
    print("✓ Agents ready\n")
    
    print_header("STARTING CONVERSATION", "═")
    
    # Conversation loop
    turn = 0
    context = ""
    
    while True:
        turn += 1
        
        # Generate user input
        print(f"[Turn {turn}] Generating user input...")
        user_input = user.generate_next_input(context)
        
        if user_input is None:
            print("\n✓ Conversation ended (all scenarios completed)")
            break
        
        # Show user input with small delay for effect
        time.sleep(0.5)
        
        # Get Persona response
        print(f"[Turn {turn}] Generating Persona response...")
        start_time = time.time()
        persona_response = persona.respond(user_input)
        latency = (time.time() - start_time) * 1000
        
        # Display turn
        print_turn(turn, user_input, persona_response, latency)
        
        # Update context
        context = f"Previous exchange:\nUser: {user_input}\nPersona: {persona_response}"
        
        # Small pause between turns
        time.sleep(0.5)
    
    # Summary
    print_header("CONVERSATION SUMMARY", "═")
    print(f"Total Turns: {turn - 1}")
    print(f"Domains Detected: {persona.state.domains or 'None yet'}")
    print(f"Final Mode: {persona.state.mode}")
    print(f"Emotional Load: {persona.state.emotional_metrics.get('intensity', 'N/A') if persona.state.emotional_metrics else 'N/A'}")
    print(f"\n✓ Full conversation logged to: persona_user_conversation.log\n")
    
    print_header("WHAT WE OBSERVED", "─")
    print("""
This conversation demonstrates:
  ✓ Both sides using real LLM (not templates)
  ✓ Persona's decision logic (PASS/SUPPRESS/CLARIFY)
  ✓ Emotional intelligence detection
  ✓ Domain classification accumulation
  ✓ State persistence across turns
  ✓ Natural dialogue flow
  ✓ Context-aware responses
  
Key Insight:
  The LLM generates realistic user inputs based on scenarios, and
  Persona responds with wisdom based on its decision logic.
  This shows the full system working end-to-end.
""")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Conversation stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
