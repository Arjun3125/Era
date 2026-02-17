#!/usr/bin/env python
"""
Launch Persona N with Synthetic Human Simulation

This script starts the Persona system in automated simulation mode,
where a synthetic user (powered by llama3.1:8b LLM) converses with 
Persona N (powered by qwen3:14b LLM) in real-time.

The conversation demonstrates:
- Mode-based decision orchestration (MEETING mode by default)  
- Mode-aware council routing (relevant ministers for each mode)
- Real-time synthetic dialogue between two LLM agents
- Mode metrics tracking for performance analysis

Run this with:
    python run_persona_conversation.py
"""

import os
import sys

# Enable automated simulation
os.environ['AUTOMATED_SIMULATION'] = '1'
os.environ['PERSONA_DEBUG'] = '1'

# Ensure unbuffered output
sys.dont_write_bytecode = False

print("=" * 70)
print("PERSONA N - AUTOMATED SYNTHETIC CONVERSATION SYSTEM")
print("=" * 70)
print()
print("Starting Persona N with synthetic user simulation...")
print("- User LLM: llama3.1:8b-instruct-q4_0 (generates user responses)")
print("- Program LLM: qwen3:14b (Persona N's responses)")
print("- Mode: Auto-selected MEETING (balanced, 3-5 relevant ministers)")
print()
print("Watch the real-time conversation between Synthetic User and Persona N:")
print("-" * 70)
print()

# Import and run main
try:
    from persona.main import main
    main()
except KeyboardInterrupt:
    print("\n\n[INTERRUPTED] Conversation terminated by user")
    sys.exit(0)
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
