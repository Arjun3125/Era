"""
ML-Integrated Conversation System: Verification & Quick Test

Verifies all components are properly integrated and working.
"""

import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))


def verify_imports():
    """Verify all required imports work."""
    print("\n" + "="*70)
    print("1️⃣  VERIFYING IMPORTS")
    print("="*70 + "\n")
    
    checks = []
    
    # LLM components
    try:
        from persona.ollama_runtime import OllamaRuntime
        checks.append(("✅", "OllamaRuntime", "persona/ollama_runtime.py"))
    except Exception as e:
        checks.append(("❌", "OllamaRuntime", str(e)))
    
    # Domain detection
    try:
        from persona.domain_detector import analyze_situation
        checks.append(("✅", "Domain Detector", "persona/domain_detector.py"))
    except Exception as e:
        checks.append(("❌", "Domain Detector", str(e)))
    
    # Session management
    try:
        from persona.session_manager import SessionManager
        checks.append(("✅", "SessionManager", "persona/session_manager.py"))
    except Exception as e:
        checks.append(("❌", "SessionManager", str(e)))
    
    # Learning components
    try:
        from persona.learning.episodic_memory import EpisodicMemory, Episode
        checks.append(("✅", "EpisodicMemory", "persona/learning/episodic_memory.py"))
    except Exception as e:
        checks.append(("❌", "EpisodicMemory", str(e)))
    
    try:
        from persona.learning.performance_metrics import PerformanceMetrics
        checks.append(("✅", "PerformanceMetrics", "persona/learning/performance_metrics.py"))
    except Exception as e:
        checks.append(("❌", "PerformanceMetrics", str(e)))
    
    # ML components
    try:
        from ml.ml_orchestrator import MLWisdomOrchestrator
        checks.append(("✅", "MLWisdomOrchestrator", "ml/ml_orchestrator.py"))
    except Exception as e:
        checks.append(("❌", "MLWisdomOrchestrator", str(e)))
    
    try:
        from persona.modes.mode_orchestrator import ModeOrchestrator
        checks.append(("✅", "ModeOrchestrator", "persona/modes/mode_orchestrator.py"))
    except Exception as e:
        checks.append(("❌", "ModeOrchestrator", str(e)))
    
    # Knowledge engine
    try:
        from persona.knowledge_engine import synthesize_knowledge
        checks.append(("✅", "KnowledgeEngine", "persona/knowledge_engine.py"))
    except Exception as e:
        checks.append(("❌", "KnowledgeEngine", str(e)))
    
    # Main system
    try:
        from ml_integrated_conversation import MLIntegratedConversation
        checks.append(("✅", "MLIntegratedConversation", "ml_integrated_conversation.py"))
    except Exception as e:
        checks.append(("❌", "MLIntegratedConversation", str(e)))
    
    for status, component, source in checks:
        print(f"  {status} {component:30} {source}")
    
    passed = len([c for c in checks if c[0] == "✅"])
    total = len(checks)
    print(f"\n  {passed}/{total} imports successful")
    
    return passed == total


def verify_directories():
    """Verify required directories exist."""
    print("\n" + "="*70)
    print("2️⃣  VERIFYING DIRECTORIES")
    print("="*70 + "\n")
    
    required_dirs = [
        "data/sessions",
        "data/conversations",
        "data/memory",
        "data/learning_insights",
        "ml/cache",
        "persona/learning",
        "persona/modes",
    ]
    
    checks = []
    for directory in required_dirs:
        path = Path(directory)
        if path.exists():
            checks.append(("✅", directory))
        else:
            # Try to create it
            try:
                path.mkdir(parents=True, exist_ok=True)
                checks.append(("✅", f"{directory} (created)"))
            except Exception as e:
                checks.append(("❌", f"{directory}: {e}"))
    
    for status, directory in checks:
        print(f"  {status} {directory}")
    
    passed = len([c for c in checks if c[0] == "✅"])
    total = len(checks)
    print(f"\n  {passed}/{total} directories ready")
    
    return passed == total


def test_llm_connection():
    """Test LLM connectivity."""
    print("\n" + "="*70)
    print("3️⃣  TESTING LLM CONNECTIVITY")
    print("="*70 + "\n")
    
    try:
        from persona.ollama_runtime import OllamaRuntime
        
        print("  Testing connection to Ollama...")
        llm = OllamaRuntime(
            speak_model="qwen3:14b",
            analyze_model="qwen3:14b"
        )
        
        test_prompt = "Respond briefly with 'OK' if you can read this."
        response = llm.analyze(
            system_prompt="You are a simple test assistant.",
            user_prompt=test_prompt
        )
        
        if response and len(response) > 0:
            print(f"  ✅ Ollama connected")
            print(f"  ✅ Model response: {response[:50]}...")
            return True
        else:
            print(f"  ❌ No response from model")
            return False
            
    except Exception as e:
        print(f"  ❌ LLM connection failed: {e}")
        print("\n     Make sure Ollama is running:")
        print("     $ ollama serve")
        return False


def test_domain_detection():
    """Test domain detection."""
    print("\n" + "="*70)
    print("4️⃣  TESTING DOMAIN DETECTION")
    print("="*70 + "\n")
    
    try:
        from persona.domain_detector import analyze_situation
        
        test_problem = "I'm considering a career change but worried about financial impact."
        
        print(f"  Testing: \"{test_problem}\"")
        analysis = analyze_situation(test_problem, llm_adapter=None)
        
        domains = analysis.get("domains", [])
        stakes = analysis.get("stakes", "unknown")
        
        print(f"  ✅ Domain detection works")
        print(f"     Domains: {', '.join(domains)}")
        print(f"     Stakes: {stakes}")
        
        return len(domains) > 0
        
    except Exception as e:
        print(f"  ❌ Domain detection failed: {e}")
        return False


def test_session_manager():
    """Test session manager."""
    print("\n" + "="*70)
    print("5️⃣  TESTING SESSION MANAGER")
    print("="*70 + "\n")
    
    try:
        from persona.session_manager import SessionManager
        
        manager = SessionManager()
        
        session = manager.start_session(
            problem_statement="Test problem",
            domains=["career"],
            domain_confidence=0.85,
            stakes="medium",
            reversibility="reversible"
        )
        
        print(f"  ✅ SessionManager works")
        print(f"     Session ID: {session.session_id if hasattr(session, 'session_id') else 'Session object'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ SessionManager failed: {e}")
        return False


def test_learning_components():
    """Test learning components."""
    print("\n" + "="*70)
    print("6️⃣  TESTING LEARNING COMPONENTS")
    print("="*70 + "\n")
    
    checks = []
    
    # Test episodic memory
    try:
        from persona.learning.episodic_memory import EpisodicMemory, Episode
        
        memory = EpisodicMemory()
        episode = Episode(
            episode_id="test_episode",
            turn_id=1,
            domain="career",
            user_input="Test input",
            persona_recommendation="Test recommendation",
            confidence=0.85,
            minister_stance="Test",
            council_recommendation="Test outcome",
            outcome="success",
            regret_score=0.0
        )
        
        memory.store_episode(episode)
        checks.append(("✅", "EpisodicMemory"))
        
    except Exception as e:
        checks.append(("❌", f"EpisodicMemory: {e}"))
    
    # Test performance metrics
    try:
        from persona.learning.performance_metrics import PerformanceMetrics
        
        metrics = PerformanceMetrics()
        metrics.record_decision(
            turn=1,
            domain="career",
            recommendation="Test",
            confidence=0.85,
            outcome="success",
            regret=0.0
        )
        
        checks.append(("✅", "PerformanceMetrics"))
        
    except Exception as e:
        checks.append(("❌", f"PerformanceMetrics: {e}"))
    
    for status, component in checks:
        print(f"  {status} {component}")
    
    passed = len([c for c in checks if c[0] == "✅"])
    return passed == len(checks)


def print_summary(results):
    """Print verification summary."""
    print("\n" + "="*70)
    print("✅ VERIFICATION SUMMARY")
    print("="*70 + "\n")
    
    total = len(results)
    passed = len([r for r in results if r])
    
    print(f"  {passed}/{total} verification checks passed")
    
    if passed == total:
        print("\n  🎉 All systems ready!")
        print("\n  Next step:")
        print("    python ml_integrated_conversation.py")
    else:
        print("\n  ⚠️  Some checks failed. Review output above.")
        print("     Make sure Ollama is running: ollama serve")
    
    print("\n" + "="*70 + "\n")


def main():
    """Run all verifications."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "ML-INTEGRATED CONVERSATION SYSTEM" + " "*21 + "║")
    print("║" + " "*20 + "Verification & Setup Check" + " "*22 + "║")
    print("╚" + "="*68 + "╝")
    
    results = [
        verify_imports(),
        verify_directories(),
    ]
    
    # Optional tests (don't fail if LLM not available)
    print("\n[Optional Tests - require Ollama running]\n")
    try:
        results.append(test_llm_connection())
    except:
        print("  ⚠️  LLM test skipped (Ollama may not be running)")
        results.append(None)
    
    try:
        results.append(test_domain_detection())
    except:
        results.append(False)
    
    try:
        results.append(test_session_manager())
    except:
        results.append(False)
    
    try:
        results.append(test_learning_components())
    except:
        results.append(False)
    
    # Remove None values from optional tests
    results = [r for r in results if r is not None]
    
    print_summary(results)


if __name__ == "__main__":
    main()
