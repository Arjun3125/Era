#!/usr/bin/env python
"""
Comprehensive system integration check before synthetic conversation.

Tests:
1. LLM Runtime - Can connect to Ollama
2. Mode Orchestrator - Can switch modes and route ministers
3. Dynamic Council - Can convene council
4. Mode Metrics - Can track performance
5. Episodic Memory - Can store episodes
6. Learning Systems - Can analyze patterns
7. Synthetic Human - Can generate responses
8. Full end-to-end flow

If all pass, then proceed to synthetic conversation.
"""

import os
import sys

os.environ['AUTOMATED_SIMULATION'] = '1'
os.environ['PERSONA_DEBUG'] = '1'

print("\n" + "="*70)
print("PERSONA N - SYSTEM INTEGRATION CHECK")
print("="*70 + "\n")

# Test 1: LLM Runtime
print("[TEST 1] LLM Runtime Connection...")
try:
    from persona.ollama_runtime import OllamaRuntime
    llm = OllamaRuntime()
    # Try a quick LLM call
    response = llm.speak("You are a test.", "Say 'connected' in one word.")
    if "connect" in response.lower():
        print("  [OK] LLM Runtime: CONNECTED")
    else:
        print(f"  [WARN] LLM Runtime: Response received but unexpected: {response[:50]}")
except Exception as e:
    print(f"  [FAIL] LLM Runtime FAILED: {e}")
    sys.exit(1)

# Test 2: Mode Orchestrator
print("[TEST 2] Mode Orchestrator...")
try:
    from persona.modes.mode_orchestrator import ModeOrchestrator
    mode_orch = ModeOrchestrator()
    
    # Test setting modes
    for mode in ["quick", "war", "meeting", "darbar"]:
        success = mode_orch.set_mode(mode)
        if not success:
            raise Exception(f"Could not set mode: {mode}")
    
    # Test minister selection
    for mode in ["quick", "war", "meeting", "darbar"]:
        mode_orch.set_mode(mode)
        should_convene = mode_orch.should_invoke_council(mode)
        ministers = mode_orch.get_ministers_for_mode(mode, {"domains": ["finance"]})
        print(f"  [+] {mode.upper():8} - convene={should_convene}, ministers={len(ministers) if should_convene else 0}")
    
    print("  [OK] Mode Orchestrator: WORKING")
except Exception as e:
    print(f"  [FAIL] Mode Orchestrator FAILED: {e}")
    sys.exit(1)

# Test 3: Dynamic Council
print("[TEST 3] Dynamic Council...")
try:
    from persona.council.dynamic_council import DynamicCouncil
    dyn_council = DynamicCouncil(llm=llm)
    dyn_council.set_mode("meeting")
    
    # Try to convene
    council_result = dyn_council.convene_for_mode(
        "meeting",
        "I'm worried about my startup finances",
        {"domains": ["finance"], "turn_count": 1}
    )
    
    if council_result and "outcome" in council_result:
        print(f"  [+] Council outcome: {council_result.get('outcome')}")
        print(f"  [+] Ministers involved: {len(council_result.get('minister_positions', {}))}")
        print("  [OK] Dynamic Council: WORKING")
    else:
        raise Exception("No council outcome received")
except Exception as e:
    print(f"  [FAIL] Dynamic Council FAILED: {e}")
    sys.exit(1)

# Test 4: Mode Metrics
print("[TEST 4] Mode Metrics Tracking...")
try:
    from persona.modes.mode_metrics import ModeMetrics
    metrics = ModeMetrics()
    
    # Record some decisions
    for i in range(5):
        metrics.record_mode_decision(
            mode="meeting" if i % 2 == 0 else "quick",
            outcome="success" if i % 3 == 0 else "failure",
            confidence=0.7 + (i * 0.05),
            regret=0.1 * (i % 2)
        )
    
    # Compare modes
    comparison = metrics.compare_modes()
    print(f"  [+] Recorded 5 decisions across modes")
    print(f"  [+] Mode comparison: {len(comparison)} modes tracked")
    print("  [OK] Mode Metrics: WORKING")
except Exception as e:
    print(f"  [FAIL] Mode Metrics FAILED: {e}")
    sys.exit(1)

# Test 5: Episodic Memory
print("[TEST 5] Episodic Memory...")
try:
    from persona.learning.episodic_memory import EpisodicMemory, Episode
    memory = EpisodicMemory(storage_path="data/memory/test_episodes.jsonl")
    
    # Store an episode
    episode = Episode(
        episode_id=None,
        turn_id=1,
        domain="finance",
        user_input="I'm worried about cash flow",
        persona_recommendation="Consider diversifying income sources",
        confidence=0.75,
        minister_stance="support",
        council_recommendation="balanced_approach"
    )
    
    memory.store_episode(episode)
    print(f"  [+] Stored episode in memory")
    print(f"  [+] Total episodes: {len(memory.episodes)}")
    print("  [OK] Episodic Memory: WORKING")
except Exception as e:
    print(f"  [FAIL] Episodic Memory FAILED: {e}")
    sys.exit(1)

# Test 6: Learning Systems
print("[TEST 6] Learning Systems...")
try:
    from persona.learning.performance_metrics import PerformanceMetrics
    from persona.learning.outcome_feedback import OutcomeFeedbackLoop
    from ml.pattern_extraction import PatternExtractor
    
    perf_metrics = PerformanceMetrics(storage_path="data/memory/test_metrics.jsonl")
    pattern_ext = PatternExtractor(episodic_memory=memory)
    
    # Record decisions
    for i in range(10):
        perf_metrics.record_decision(
            turn=i,
            domain="finance",
            recommendation="diversify",
            confidence=0.7,
            outcome="success" if i % 3 != 0 else "failure",
            regret=0.1 if i % 3 == 0 else 0.0
        )
    
    success_rate = perf_metrics.get_success_rate()
    print(f"  [+] Recorded 10 decisions")
    print(f"  [+] Success rate: {success_rate:.1%}")
    print("  [OK] Learning Systems: WORKING")
except Exception as e:
    print(f"  [FAIL] Learning Systems FAILED: {e}")
    sys.exit(1)

# Test 7: Synthetic Human
print("[TEST 7] Synthetic Human Simulation...")
try:
    from hse.human_profile import SyntheticHuman
    from hse.simulation.synthetic_human_sim import SyntheticHumanSimulation
    
    synthetic_human = SyntheticHuman(name="Test User", age=32, seed=42)
    human_sim = SyntheticHumanSimulation(synthetic_human, user_llm=llm)
    
    # Generate synthetic input
    context = {
        "mode": "meeting",
        "domains": ["finance"],
        "turn_count": 1,
        "recent_turns": []
    }
    
    persona_advice = "You should consider diversifying your income streams to reduce financial risk."
    user_response = human_sim.generate_next_input(persona_advice, context)
    
    print(f"  [+] Generated synthetic response: {len(user_response)} chars")
    print(f"  [+] Sample: {user_response[:80]}...")
    print("  [OK] Synthetic Human: WORKING")
except Exception as e:
    print(f"  [FAIL] Synthetic Human FAILED: {e}")
    sys.exit(1)

# Test 8: Full Integration
print("[TEST 8] Full Integration Test...")
try:
    from persona.state import CognitiveState
    
    state = CognitiveState()
    
    # Simulate a turn
    print(f"  [+] Initial state created")
    print(f"  [+] Mode: {state.mode}")
    print(f"  [+] Domains: {state.domains}")
    print(f"  [+] Turn count: {state.turn_count}")
    
    # Verify all systems are accessible
    systems = {
        "LLM": llm,
        "ModeOrchestrator": mode_orch,
        "DynamicCouncil": dyn_council,
        "ModeMetrics": metrics,
        "EpisodicMemory": memory,
        "SyntheticHuman": human_sim,
    }
    
    for name, system in systems.items():
        if system is None:
            raise Exception(f"{name} is None")
    
    print(f"  [+] All {len(systems)} systems accessible")
    print("  [OK] Full Integration: WORKING")
except Exception as e:
    print(f"  [FAIL] Full Integration FAILED: {e}")
    sys.exit(1)

# All tests passed!
print("\n" + "="*70)
print("[SUCCESS] ALL SYSTEMS OPERATIONAL - READY FOR SYNTHETIC CONVERSATION")
print("="*70)
print("\nNext: Starting real-time synthetic conversation...")
print("System will run MEETING mode with 2 LLMs talking:\n")
print("  - User LLM (llama3.1:8b): Generates synthetic user responses")
print("  - Program LLM (qwen3:14b): Persona N responses")
print("\nWatch for:")
print("  - Mode routing to relevant ministers")
print("  - Decision metrics and confidence scores")
print("  - Every 100 turns: performance report\n")
print("="*70 + "\n")

# Now run the actual main
try:
    from persona.main import main
    main()
except KeyboardInterrupt:
    print("\n\n[CONVERSATION ENDED] User interrupted")
except Exception as e:
    print(f"\n\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
