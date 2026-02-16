#!/usr/bin/env python3
"""
Interactive Persona Chat - Talk directly with Persona in terminal
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from persona_mas_integration_simple import SimplePersonaAgent
from persona.state import CognitiveState

def interactive_chat():
    """Run interactive chat with Persona"""
    print("=" * 70)
    print("INTERACTIVE PERSONA CHAT")
    print("=" * 70)
    print("\nTalk with Persona directly!")
    print("Type 'exit' or 'quit' to end conversation\n")
    print("-" * 70)
    
    agent = SimplePersonaAgent(name="Persona")
    system_prompt = "You are Persona, an intelligent conversational assistant with deep wisdom."
    
    turn = 0
    while True:
        # Get user input
        user_input = input("\nYOU: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in {"exit", "quit"}:
            print("\nPersona: We'll continue another time. Farewell.")
            break
        
        # Get Persona response
        turn += 1
        response = agent.respond(system_prompt, user_input)
        
        # Display response
        print(f"\nPersona: {response}")
        
        # Show state tracking
        print(f"\n[State] Turn: {agent.state.turn_count}, "
              f"Domains: {agent.state.domains}, "
              f"Confidence: {agent.state.domain_confidence:.2f}")
        print("-" * 70)

if __name__ == "__main__":
    try:
        interactive_chat()
    except KeyboardInterrupt:
        print("\n\nConversation ended.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
