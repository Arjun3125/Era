"""
Quick test of ML-integrated conversation system
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("ML-INTEGRATED CONVERSATION SYSTEM - QUICK TEST")
print("="*70 + "\n")

# Test 1: Imports
print("[TEST 1] Checking imports...")
try:
    from ml_integrated_conversation import MLIntegratedConversation
    from persona.ollama_runtime import OllamaRuntime
    from persona.domain_detector import analyze_situation
    from persona.session_manager import SessionManager
    from persona.learning.episodic_memory import EpisodicMemory
    from persona.learning.performance_metrics import PerformanceMetrics
    print("  OK - All components imported successfully\n")
except Exception as e:
    print(f"  FAILED - {e}\n")
    sys.exit(1)

# Test 2: System initialization
print("[TEST 2] Initializing system...")
try:
    system = MLIntegratedConversation()
    print("  OK - System initialized\n")
except Exception as e:
    print(f"  FAILED - {e}\n")
    print("  Note: Make sure Ollama is running: ollama serve\n")

# Test 3: Components working
print("[TEST 3] Component verification...")
checks = []

# Domain detection
try:
    from persona.domain_detector import analyze_situation
    result = analyze_situation("I should change careers", llm_adapter=None)
    if result.get("domains"):
        checks.append(("Domain Detection", "OK"))
    else:
        checks.append(("Domain Detection", "WARNING - no domains detected"))
except:
    checks.append(("Domain Detection", "FAILED"))

# Session Manager
try:
    from persona.session_manager import SessionManager
    manager = SessionManager()
    session = manager.start_session(
        problem_statement="Test",
        domains=["career"],
        domain_confidence=0.85,
        stakes="medium",
        reversibility="reversible"
    )
    checks.append(("SessionManager", "OK"))
except:
    checks.append(("SessionManager", "FAILED"))

# Episodic Memory
try:
    from persona.learning.episodic_memory import EpisodicMemory, Episode
    memory = EpisodicMemory()
    episode = Episode(
        episode_id="test",
        turn_id=1,
        domain="career",
        user_input="test",
        persona_recommendation="test",
        confidence=0.8,
        minister_stance="test",
        council_recommendation="test"
    )
    memory.store_episode(episode)
    checks.append(("EpisodicMemory", "OK"))
except Exception as e:
    checks.append(("EpisodicMemory", f"FAILED - {str(e)[:40]}"))

# Performance Metrics
try:
    from persona.learning.performance_metrics import PerformanceMetrics
    metrics = PerformanceMetrics()
    metrics.record_decision(1, "career", "test", 0.8, "success")
    checks.append(("PerformanceMetrics", "OK"))
except:
    checks.append(("PerformanceMetrics", "FAILED"))

for component, status in checks:
    print(f"  {component:25} - {status}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70 + "\n")

passed = len([c for c in checks if "OK" in c[1]])
total = len(checks)

if passed == total:
    print(f"  PASSED: {passed}/{total} components verified")
    print("\n  System is ready to use!")
    print("  Run: python ml_integrated_conversation.py\n")
else:
    print(f"  WARNING: {passed}/{total} components working")
    print("\n  Some features may not work.")
    print("  Make sure Ollama is running: ollama serve\n")

print("="*70 + "\n")
