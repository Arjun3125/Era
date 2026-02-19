#!/usr/bin/env python3
"""
Direct LLM-to-LLM Conversation Engine

Enables User LLM (deepseek-r1:8b) and Program LLM (qwen3:14b) 
to have natural back-and-forth conversations on any topic.

Usage:
    python llm_conversation.py              # Interactive mode
    python llm_conversation.py --topic "..." # Specific topic
    python llm_conversation.py --rounds N    # Set conversation rounds
"""

import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Import LLM runtime
sys.path.insert(0, str(Path(__file__).parent))
from persona.ollama_runtime import OllamaRuntime


class LLMConversation:
    """Direct conversation between User LLM and Program LLM."""
    
    def __init__(self, verbose=False, max_rounds=10):
        """Initialize LLM conversation engine."""
        self.verbose = verbose
        self.max_rounds = max_rounds
        self.conversation_history = []
        
        # Initialize both LLM runtimes
        print("[Init] Starting LLM runtimes...")
        self.user_llm = OllamaRuntime(
            speak_model="deepseek-r1:8b",
            analyze_model="deepseek-r1:8b"
        )
        self.program_llm = OllamaRuntime(
            speak_model="qwen3:14b",
            analyze_model="qwen3:14b"
        )
        print("  [OK] User LLM ready (deepseek-r1:8b)")
        print("  [OK] Program LLM ready (qwen3:14b)")
    
    def start_conversation(self, topic=None):
        """Start a conversation between the two LLMs."""
        
        if topic is None:
            print("\n" + "="*70)
            print("LLM-TO-LLM CONVERSATION ENGINE")
            print("="*70)
            print("\nEnter a topic for the LLMs to discuss.")
            print("Examples:")
            print("  • The future of AI in decision-making")
            print("  • Should machines have rights?")
            print("  • Best practices for remote work")
            print("  • How to make better decisions under uncertainty")
            print()
            topic = input("Topic: ").strip()
            
            if not topic:
                topic = "The nature of intelligent decision-making"
                print(f"Using default topic: {topic}")
        
        print(f"\n{'='*70}")
        print(f"Topic: {topic}")
        print(f"{'='*70}\n")
        
        # User LLM starts the conversation
        print("[User LLM] Initiating conversation...")
        opening = self.user_llm.analyze(
            system_prompt="You are an insightful conversationalist. Start engaging discussions thoughtfully.",
            user_prompt=f"Let's discuss: {topic}\n\nShare your initial thoughts."
        )
        
        print(f"\n[User LLM]")
        print(f"{opening}\n")
        
        self.conversation_history.append({
            "round": 1,
            "speaker": "User LLM",
            "text": opening,
            "role": "initiator"
        })
        
        # Rounds of back-and-forth
        for round_num in range(2, self.max_rounds + 1):
            print(f"{'-'*70}")
            print(f"ROUND {round_num}")
            print(f"{'-'*70}\n")
            
            # Program LLM responds
            program_response = self.program_llm.analyze(
                system_prompt="You are a thoughtful participant in a discussion. Build on the previous point.",
                user_prompt=f"Topic: {topic}\n\nPrevious point:\n{opening if round_num == 2 else self.conversation_history[-1]['text']}\n\nYour response:"
            )
            
            print(f"[Program LLM]")
            print(f"{program_response}\n")
            
            self.conversation_history.append({
                "round": round_num,
                "speaker": "Program LLM",
                "text": program_response,
                "role": "responder"
            })
            
            # User LLM responds to Program LLM
            user_response = self.user_llm.analyze(
                system_prompt="You are engaging in thoughtful dialogue. Respond to the other point.",
                user_prompt=f"Topic: {topic}\n\nTheir perspective:\n{program_response}\n\nYour thoughtful reply:"
            )
            
            print(f"[User LLM]")
            print(f"{user_response}\n")
            
            self.conversation_history.append({
                "round": round_num,
                "speaker": "User LLM",
                "text": user_response,
                "role": "responder"
            })
            
            opening = user_response  # Update for next iteration
    
    def run_interactive(self):
        """Interactive loop for multiple conversations."""
        
        print("\n" + "="*70)
        print("INTERACTIVE LLM CONVERSATION MODE")
        print("="*70)
        print("\nCommands:")
        print("  • Enter a topic to start conversation")
        print("  • 'save' to save current conversation")
        print("  • 'show' to display current conversation")
        print("  • 'clear' to start fresh")
        print("  • 'quit' to exit\n")
        
        session_num = 0
        
        while True:
            user_input = input("Enter topic (or command): ").strip().lower()
            
            if user_input == "quit":
                print("Goodbye!")
                break
            elif user_input == "save":
                self._save_conversation()
            elif user_input == "show":
                self._display_conversation()
            elif user_input == "clear":
                self.conversation_history = []
                print("Conversation cleared.")
            elif user_input:
                session_num += 1
                print(f"\n[Conversation {session_num}]")
                self.start_conversation(topic=user_input)
                
                # Ask if user wants to save
                save_choice = input("\nSave this conversation? (y/n): ").strip().lower()
                if save_choice == 'y':
                    self._save_conversation()
    
    def _save_conversation(self):
        """Save conversation to file."""
        
        if not self.conversation_history:
            print("No conversation to save.")
            return
        
        # Create sessions directory
        sessions_dir = Path("data/conversations")
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = sessions_dir / f"llm_conversation_{timestamp}.json"
        
        # Save data
        data = {
            "timestamp": datetime.now().isoformat(),
            "rounds": len(self.conversation_history),
            "conversation": self.conversation_history
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"[OK] Saved to {filename}")
    
    def _display_conversation(self):
        """Display current conversation."""
        
        if not self.conversation_history:
            print("No conversation to display.")
            return
        
        print("\n" + "="*70)
        print("CONVERSATION HISTORY")
        print("="*70 + "\n")
        
        for entry in self.conversation_history:
            print(f"[{entry['speaker']} - Round {entry['round']}]")
            print(f"{entry['text']}\n")
            print("-"*70 + "\n")
    
    def demo_conversation(self):
        """Run a demo conversation with a preset topic."""
        
        topic = "The future of intelligent decision systems"
        print("\n" + "="*70)
        print("DEMO: LLM-TO-LLM CONVERSATION")
        print("="*70)
        print(f"Topic: {topic}\n")
        
        self.start_conversation(topic=topic)
        
        # Save demo
        self._save_conversation()


def main():
    parser = argparse.ArgumentParser(
        description="Direct LLM-to-LLM conversation engine",
        allow_abbrev=False
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "demo", "topic"],
        default="interactive",
        help="Conversation mode"
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Topic for discussion (topic mode)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="Number of conversation rounds"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Create conversation engine
    engine = LLMConversation(
        verbose=args.verbose,
        max_rounds=args.rounds
    )
    
    # Run appropriate mode
    if args.mode == "demo":
        engine.demo_conversation()
    elif args.mode == "topic":
        if args.topic:
            engine.start_conversation(topic=args.topic)
            engine._save_conversation()
        else:
            print("Error: --topic required for topic mode")
            sys.exit(1)
    else:  # interactive
        engine.run_interactive()


if __name__ == "__main__":
    main()
