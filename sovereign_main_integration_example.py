# sovereign_main_integration_example.py
"""
Example integration of SovereignOrchestrator into a main simulation loop.
Shows how to use all 12 cognitive systems together.
"""

from ml.sovereign_orchestrator import SovereignOrchestrator
# Import your existing systems: council, kis_engine, call_model, etc.


def main_simulation_loop(
    council,
    kis_engine,
    persona_doctrine,
    user_llm,
    call_model,
    synthetic_human=None,
    max_turns=1000,
    use_synthetic_human=True
):
    """
    Main simulation loop with full orchestration.
    
    Args:
        council: CouncilAggregator (DARBAR ministers)
        kis_engine: KnowledgeEngine (KIS)
        persona_doctrine: Doctrine structure
        user_llm: LLM for synthetic human
        call_model: LLM for Persona
        synthetic_human: SyntheticHuman instance
        max_turns: Maximum simulation turns
        use_synthetic_human: If False, use manual input
    """
    
    print("\n" + "="*70)
    print("🚀 SOVEREIGN ORCHESTRATOR SIMULATION")
    print("="*70 + "\n")
    
    # Initialize orchestrator
    orchestrator = SovereignOrchestrator(
        council=council,
        kis_engine=kis_engine,
        persona_doctrine=persona_doctrine,
        user_llm=user_llm,
        call_model=call_model
    )
    
    # Attach synthetic human if provided
    if use_synthetic_human and synthetic_human:
        orchestrator.initialize_synthetic_human(synthetic_human)
    
    # Initial problem setup
    current_domain = "wealth"
    current_input = synthetic_human.story_prompt if synthetic_human else "I need strategic direction."
    
    # Phase markers
    phase_1_complete = False
    phase_2_complete = False
    phase_3_complete = False
    
    # Crisis scenarios for Phase 4
    compounding_crisis = [
        {"turn_offset": 0, "domain": "wealth", "severity": 0.6},
        {"turn_offset": 20, "domain": "wealth", "severity": 0.9},
        {"turn_offset": 40, "domain": "health", "severity": 0.7},
        {"turn_offset": 60, "domain": "relationships", "severity": 0.8},
        {"turn_offset": 100, "domain": "career", "severity": 0.85}
    ]
    
    # Main simulation loop
    turn = 0
    while turn < max_turns:
        turn += 1
        
        print(f"\n{'─'*70}")
        print(f"TURN {turn} / {max_turns}")
        print(f"{'─'*70}")
        
        # ================================================================
        # DETERMINE PHASE
        # ================================================================
        
        if turn == 100:
            phase_1_complete = True
            print("\n✅ PHASE 1 COMPLETE: Infrastructure ready\n")
        
        if turn == 300:
            phase_2_complete = True
            print("\n✅ PHASE 2 COMPLETE: Learning loop active\n")
        
        if turn == 700:
            phase_3_complete = True
            print("\n✅ PHASE 3 COMPLETE: Optimization ready\n")
        
        # ================================================================
        # GET USER INPUT
        # ================================================================
        
        if use_synthetic_human and orchestrator.human_sim:
            # Synthetic human input
            user_input = current_input
            print(f"👤 Human: {user_input[:80]}...")
        else:
            # Manual input for testing
            user_input = input("\n💬 Enter: ")
        
        # ================================================================
        # DETERMINE CURRENT MODE & DOMAIN
        # ================================================================
        
        # Simple mode selection (can be more sophisticated)
        if turn % 20 == 0:
            current_mode = "darbar"  # Full analysis every 20 turns
        elif turn % 5 == 0:
            current_mode = "meeting"  # Structured updates
        else:
            current_mode = "quick"  # Fast decisions
        
        # Domain detection (simplified)
        if "wealth" in user_input.lower() or "money" in user_input.lower():
            current_domain = "wealth"
        elif "health" in user_input.lower():
            current_domain = "health"
        elif "relationship" in user_input.lower():
            current_domain = "relationships"
        else:
            current_domain = "strategic"
        
        # ================================================================
        # CALL PERSONA (YOUR EXISTING LOGIC)
        # ================================================================
        
        # This is where your existing persona generation happens
        persona_response = generate_persona_response(
            user_input,
            current_mode,
            current_domain,
            council,
            kis_engine
        )
        
        print(f"\n🤖 Persona ({current_mode}): {persona_response[:150]}...")
        
        # ================================================================
        # GET MINISTER VOTES & KNOWLEDGE USED (FROM YOUR LOGIC)
        # ================================================================
        
        minister_votes = {
            "Risk": "moderate",
            "Strategy": "aggressive" if turn % 3 == 0 else "balanced",
            "Wisdom": "cautious"
        }
        
        knowledge_items_used = ["item_42", "item_17"] if turn % 10 == 0 else []
        doctrine_applied = "wealth_growth" if current_domain == "wealth" else None
        
        # ================================================================
        # DETERMINE CRISIS ACTIVATION
        # ================================================================
        
        crisis_active = None
        if phase_3_complete and turn >= 700:
            # Activate compounding crisis in Phase 4
            scenario_elapsed = turn - 700
            for stage in compounding_crisis:
                if scenario_elapsed == stage["turn_offset"]:
                    crisis_active = compounding_crisis
                    print(f"\n🔥 CRISIS SCENARIO ACTIVATED")
                    break
        
        # ================================================================
        # RUN ORCHESTRATION TURN
        # ================================================================
        
        result = orchestrator.run_turn(
            turn=turn,
            user_input=user_input,
            persona_response=persona_response,
            current_domain=current_domain,
            current_mode=current_mode,
            minister_votes=minister_votes,
            knowledge_items_used=knowledge_items_used,
            doctrine_applied=doctrine_applied,
            emotional_distortion_detected=False,
            crisis_active=crisis_active
        )
        
        # ================================================================
        # DISPLAY RESULTS
        # ================================================================
        
        # Show alerts
        if result['alerts']:
            for alert in result['alerts'][:5]:  # Show top 5 alerts
                print(f"  {alert}")
        
        # Show outcome
        if result['outcome']:
            outcome_emoji = "✅" if result['outcome'] == "success" else "❌"
            print(f"\n{outcome_emoji} Outcome: {result['outcome'].upper()}")
        
        # Show next input
        if result['next_input']:
            current_input = result['next_input']
        
        # Show metrics
        if result['metrics']:
            print(f"\n📈 Metrics: {result['metrics']}")
        
        # Show failure analysis if applicable
        if result['failure_report']:
            print(f"\n🔍 Failure Analysis:")
            print(f"  Root Causes: {result['failure_report']['root_causes']}")
            print(f"  Recommendations: {result['failure_report']['recommendations']}")
        
        # ================================================================
        # PERIODIC CHECKPOINTS
        # ================================================================
        
        if turn % 50 == 0:
            state = orchestrator.get_state_snapshot()
            print(f"\n📸 CHECKPOINT T{turn}:")
            print(f"  Confidence: {state['confidence']}")
            print(f"  Memory Episodes: {state['memory_episodes']}")
            print(f"  Mode Switches: {state['mode_switches']}")
            print(f"  Arc Status: {state['arc_status']}")
    
    # ================================================================
    # FINAL REPORT
    # ================================================================
    
    print(f"\n\n{'='*70}")
    print("🏁 SIMULATION COMPLETE")
    print(f"{'='*70}\n")
    
    orchestrator._generate_report(max_turns, {})
    
    return orchestrator


def generate_persona_response(user_input, mode, domain, council, kis_engine):
    """
    Placeholder for your existing persona generation logic.
    Replace with actual implementation.
    """
    
    # This would call your existing DARBAR/council system
    # and KIS knowledge engine
    
    if mode == "quick":
        return "Quick decision: proceed with caution."
    elif mode == "meeting":
        return "1. Assess situation\n2. Consult ministers\n3. Decide strategically"
    elif mode == "darbar":
        return (
            "Calling full council. Ministers propose:\n"
            "- Risk: Conservative approach\n"
            "- Strategy: Bold expansion\n"
            "- Wisdom: Patience and preparation\n"
            "Synthesis: Measured growth with risk hedging."
        )
    else:
        return "Strategic response: evaluate all factors."


if __name__ == "__main__":
    
    # Import your existing components
    # from your_system import council, kis_engine, call_model
    # from hse.human_profile import SyntheticHuman
    
    # Placeholder
    council = None
    kis_engine = None
    persona_doctrine = {}
    user_llm = None
    call_model = None
    
    # Create synthetic human (would come from HSE)
    # synthetic_human = SyntheticHuman(name="Test Subject", age=32)
    synthetic_human = None
    
    # Run simulation
    try:
        orchestrator = main_simulation_loop(
            council=council,
            kis_engine=kis_engine,
            persona_doctrine=persona_doctrine,
            user_llm=user_llm,
            call_model=call_model,
            synthetic_human=synthetic_human,
            max_turns=1000,
            use_synthetic_human=True
        )
        print("\n✅ Simulation completed successfully")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
