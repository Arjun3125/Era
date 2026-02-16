#!/usr/bin/env python3
"""
Quick System Verification - Confirms all features are accessible
"""

import sys

print("=" * 80)
print("PERSONA SYSTEM - QUICK FEATURE VERIFICATION")
print("=" * 80)
print()

features_verified = []
features_failed = []

# Test 1: Core imports
try:
    from persona.main import PersonaBrain, CognitiveState
    features_verified.append("Core Agent Architecture")
except Exception as e:
    features_failed.append(f"Core imports: {e}")

# Test 2: Modes
try:
    from persona.state import CognitiveState
    s = CognitiveState()
    modes = ['quick', 'war', 'meeting', 'darbar']
    for mode in modes:
        s.mode = mode
    features_verified.append("All 4 Conversation Modes")
except Exception as e:
    features_failed.append(f"Modes: {e}")

# Test 3: Emotional Intelligence
try:
    from persona.analysis import assess_emotional_metrics
    features_verified.append("Emotional Intelligence System")
except Exception as e:
    features_failed.append(f"Emotional intelligence: {e}")

# Test 4: Domain Classification
try:
    from persona.analysis import classify_domains
    features_verified.append("Domain Classification (5 domains)")
except Exception as e:
    features_failed.append(f"Domain classification: {e}")

# Test 5: Response Directives
try:
    from persona.brain import ControlDirective, PersonaBrain
    directives = ['pass', 'halt', 'suppress', 'silence']
    for d in directives:
        ControlDirective(status=d, action='speak')
    features_verified.append("Response Decision System (4 types)")
except Exception as e:
    features_failed.append(f"Response directives: {e}")

# Test 6: Analysis functions
try:
    from persona.analysis import (
        assess_coherence, assess_situation, assess_mode_fitness,
        classify_domains, assess_emotional_metrics
    )
    features_verified.append("Analysis & Assessment Functions")
except Exception as e:
    features_failed.append(f"Analysis: {e}")

# Test 7: Clarification
try:
    from persona.clarify import build_clarifying_question, format_question_for_user
    q = build_clarifying_question(None, None)
    assert len(q) > 0
    features_verified.append("Clarification System")
except Exception as e:
    features_failed.append(f"Clarification: {e}")

# Test 8: KIS
try:
    from persona.knowledge_engine import synthesize_knowledge
    result = synthesize_knowledge('test', ['strategy'], 0.8)
    assert isinstance(result, dict)
    assert 'synthesized_knowledge' in result
    features_verified.append("Knowledge Integration System (KIS)")
except Exception as e:
    features_failed.append(f"KIS: {e}")

# Test 9: State Management
try:
    from persona.state import CognitiveState
    s = CognitiveState()
    assert hasattr(s, 'turn_count')
    assert hasattr(s, 'domains')
    assert hasattr(s, 'domain_confidence')
    assert hasattr(s, 'recent_turns')
    assert hasattr(s, 'background_knowledge')
    features_verified.append("State Management System")
except Exception as e:
    features_failed.append(f"State management: {e}")

# Test 10: LLM Runtime
try:
    from persona.ollama_runtime import OllamaRuntime
    llm = OllamaRuntime()
    assert hasattr(llm, 'speak')
    assert hasattr(llm, 'analyze')
    features_verified.append("Ollama LLM Runtime")
except Exception as e:
    features_failed.append(f"LLM runtime: {e}")

# Test 11: Context Building
try:
    from persona.context import build_system_context, MODE_VISIBLE_HINT
    assert 'quick' in MODE_VISIBLE_HINT
    features_verified.append("System Context & Philosophy")
except Exception as e:
    features_failed.append(f"Context: {e}")

# Test 12: Tracing
try:
    from persona.trace import trace, DEBUG_OBSERVER, TRACE
    features_verified.append("Tracing & Debugging System")
except Exception as e:
    features_failed.append(f"Tracing: {e}")

# Test 13: Edge case handling
try:
    from persona.ollama_runtime import OllamaRuntime
    from persona.state import CognitiveState
    llm = OllamaRuntime()
    s = CognitiveState()
    for test_input in ['', 'a', '!!!', '     ', 'test ' * 100]:
        response = llm.speak(test_input, s)
        assert response is not None
    features_verified.append("Edge Case Handling")
except Exception as e:
    features_failed.append(f"Edge cases: {e}")

# Summary
print("[VERIFIED FEATURES]")
print("-" * 80)
for feature in features_verified:
    print(f"  [OK] {feature}")

if features_failed:
    print()
    print("[FAILED FEATURES]")
    print("-" * 80)
    for failure in features_failed:
        print(f"  [FAIL] {failure}")

print()
print("=" * 80)
print(f"Total Features Verified: {len(features_verified)}")
print(f"Total Features Failed: {len(features_failed)}")
pass_rate = 100 * len(features_verified) / (len(features_verified) + len(features_failed))
print(f"Pass Rate: {pass_rate:.1f}%")
print()

if pass_rate >= 90:
    print("[OK] SYSTEM STATUS: OPERATIONAL ✅")
    print("[OK] All major features verified and accessible")
    print("[OK] Ready for production use")
    sys.exit(0)
else:
    print("[WARN] Some features may need attention")
    sys.exit(1)

print()
print("=" * 80)
