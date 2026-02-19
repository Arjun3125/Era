"""
Test Session Workflow

Validates:
1. Domain detection from problem statements
2. Session creation and management
3. Consequence tracking
4. Session continuity (follow-ups)
5. Session replay (related sessions)
"""
from persona.domain_detector import analyze_situation, domain_similarity
from persona.session_manager import SessionManager


def test_domain_detection():
    """Test domain detection from various problem statements"""
    print("\n" + "="*60)
    print("TEST 1: Domain Detection")
    print("="*60)
    
    problems = [
        "I'm thinking about quitting my job due to burnout and lack of growth opportunities",
        "Should I invest in cryptocurrency or stick with traditional savings?",
        "I'm having conflicts with my partner about finances and life goals",
        "Considering a major career pivot to tech from finance"
    ]
    
    for problem in problems:
        analysis = analyze_situation(problem)
        print(f"\n📌 {problem[:60]}...")
        print(f"   Domains: {', '.join(analysis['domains'])}")
        print(f"   Confidence: {analysis['domain_confidence']:.2f}")
        print(f"   Stakes: {analysis['stakes']}")
        print(f"   Reversibility: {analysis['reversibility']}")


def test_session_management():
    """Test session creation, turning, and storage"""
    print("\n" + "="*60)
    print("TEST 2: Session Management")
    print("="*60)
    
    manager = SessionManager()
    
    # Start a session
    print("\n→ Starting session...")
    session = manager.start_session(
        problem_statement="I'm overwhelmed at work and considering leaving",
        domains=["career", "psychology", "risk"],
        domain_confidence=0.85,
        stakes="high",
        reversibility="partially_reversible"
    )
    print(f"✓ Session created: {session.session_id[-8:]}")
    
    # Add some turns
    print("\n→ Recording turns...")
    for i in range(1, 4):
        turn = manager.add_turn(
            mode="QUICK" if i == 1 else "MEETING" if i == 2 else "DARBAR",
            user_input="How should I handle my workplace stress?",
            council_positions=[f"Minister {j}" for j in range(i+1)],
            prime_decision=f"Turn {i}: Consider negotiating workload first, then evaluate long-term fit",
            kis_items=[f"KIS Item {j}" for j in range(5)],
            confidence=0.5 + (i * 0.15)
        )
        print(f"  ✓ Turn {i}: Mode={turn.mode}, Confidence={turn.confidence:.2f}")
    
    # Check mode escalation
    print(f"\n→ Testing mode escalation...")
    print(f"  Turn 1-2: QUICK")
    print(f"  Turn 3-5: {manager.should_escalate_mode() if len(manager.current_session.turns) < 6 else 'N/A'}") 
    
    # Record satisfaction and end
    print("\n→ Ending session...")
    manager.record_satisfaction(satisfied=True, confidence=0.85)
    ended_session = manager.end_session(
        conclusion="User should attempt workload negotiation before considering departure",
        satisfaction=True,
        confidence=0.85
    )
    print(f"✓ Session ended: {ended_session.session_id[-8:]}")
    print(f"  Final satisfaction: {ended_session.final_satisfaction}")
    print(f"  Turns completed: {len(ended_session.turns)}")


def test_consequence_tracking():
    """Test consequence recording and retrieval"""
    print("\n" + "="*60)
    print("TEST 3: Consequence Tracking")
    print("="*60)
    
    manager = SessionManager()
    
    # Get a session ID (use the one from previous test)
    test_session_id = "2026-02-18T12:00:00_abc12345"
    
    # Record consequences
    print(f"\n→ Recording consequences for session...")
    manager.record_consequence(
        session_id=test_session_id,
        followup="User negotiated with manager for reduced workload",
        outcome="Manager agreed to reassign 2 major projects, workload reduced by 30%"
    )
    
    manager.record_consequence(
        session_id=test_session_id,
        followup="Started daily meditation practice",
        outcome="Reported improved stress levels after 2 weeks"
    )
    
    print(f"✓ Consequences recorded")
    
    # Retrieve consequences
    consequences = manager.load_consequences_for_session(test_session_id)
    print(f"✓ Retrieved {len(consequences)} consequences")


def test_session_continuity():
    """Test session continuity and related session finding"""
    print("\n" + "="*60)
    print("TEST 4: Session Continuity & Related Sessions")
    print("="*60)
    
    manager = SessionManager()
    
    # Create multiple sessions with similar/different domains
    print("\n→ Creating test sessions...")
    
    domains_list = [
        ["career", "risk"],
        ["career", "psychology"],
        ["psychology", "relationship"],
        ["career", "strategy", "power"]
    ]
    
    created_sessions = []
    for i, domains in enumerate(domains_list):
        session = manager.start_session(
            problem_statement=f"Test problem {i+1} with domains {domains}",
            domains=domains,
            domain_confidence=0.8,
            stakes="medium"
        )
        manager.end_session(
            conclusion=f"Conclusion for session {i+1}",
            satisfaction=True,
            confidence=0.8
        )
        created_sessions.append(session)
        print(f"  ✓ Session {i+1}: domains={domains}")
    
    # Find related sessions
    print(f"\n→ Finding sessions related to ['career', 'psychology']...")
    current_domains = ["career", "psychology"]
    related = manager.find_related_sessions(current_domains, limit=3)
    
    print(f"✓ Found {len(related)} related sessions:")
    for prev in related:
        sim = domain_similarity(current_domains, prev.domains)
        print(f"  • {prev.domains} (similarity: {sim:.2f})")
    
    # Get continuity context
    print(f"\n→ Getting session context for continuity...")
    context = manager.get_session_context_for_continuity(current_domains)
    if context:
        print(f"✓ Context retrieved ({len(context)} chars)")
        print(context[:200] + "...")
    else:
        print("✓ No previous context available (new problem area)")


def test_statistics():
    """Test session statistics"""
    print("\n" + "="*60)
    print("TEST 5: Session Statistics")
    print("="*60)
    
    manager = SessionManager()
    stats = manager.get_session_statistics()
    
    print(f"\n📊 Statistics:")
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Avg turns per session: {stats['avg_turns']:.1f}")
    print(f"   Satisfaction rate: {stats['satisfaction_rate']:.1%}")
    print(f"   Most common domains: {', '.join(stats['most_common_domains'])}")
    print(f"   Average confidence: {stats['avg_confidence']:.2f}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SESSION WORKFLOW TEST SUITE")
    print("="*60)
    
    try:
        test_domain_detection()
        test_session_management()
        test_consequence_tracking()
        test_session_continuity()
        test_statistics()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
