"""
Example usage of Minister Modules with KIS and Prime Confident integration.

Location: c:\era\sovereign\ministers\examples.py

This example shows:
1. Running individual minister module
2. Running all ministers via orchestrator
3. Integrating with Prime Confident for final decision
4. Accessing KIS data and execution traces
"""

from typing import Dict, Any


def example_individual_minister():
    """Example: Using an individual minister module."""
    print("\n=== EXAMPLE 1: Individual Minister Module ===\n")
    
    from sovereign.ministers.adaptation import adaptation_module
    
    user_input = "I think we need to change our approach to this problem"
    context = {
        "domains": ["adaptation", "data", "diplomacy"],
        "turn_count": 5,
        "user_input": user_input
    }
    
    # Analyze with domain-specific KIS
    output = adaptation_module.analyze(user_input, context)
    
    print(f"Minister: {output.minister_name}")
    print(f"Domain: {output.domain}")
    print(f"Stance: {output.stance}")
    print(f"Confidence: {output.confidence:.2f}")
    print(f"Reasoning: {output.reasoning}")
    print(f"KIS Items: {len(output.kis_data.get('synthesized_knowledge', []))}")
    
    # Adaptation-specific KIS
    if "adaptation_signals" in output.kis_data:
        print(f"Adaptation Signals: {output.kis_data['adaptation_signals']}")


def example_orchestrator_all_ministers():
    """Example: Running all ministers via orchestrator."""
    print("\n=== EXAMPLE 2: Orchestrator (All Ministers) ===\n")
    
    from sovereign.ministers.orchestrator import get_orchestrator
    
    user_input = "I should invest heavily in this new opportunity"
    context = {
        "domains": ["risk", "data", "power"],
        "turn_count": 3,
        "risk_level": 0.6,
        "user_input": user_input
    }
    
    orchestrator = get_orchestrator()
    flow_result = orchestrator.execute_ministers(user_input, context)
    
    print(f"Total Ministers: {len(flow_result.minister_outputs)}")
    print(f"Judges (Advisory): {len(flow_result.judge_observations)}")
    print(f"\nTotal KIS Items Generated: {flow_result.kis_summary['total_kis_items']}")
    print(f"Domains with KIS: {flow_result.kis_summary['domains_with_kis']}")
    
    print(f"\nCouncil Recommendation: {flow_result.council_recommendation.recommendation}")
    print(f"Consensus Strength: {flow_result.council_recommendation.consensus_strength:.2%}")
    
    print("\nExecution Trace:")
    for trace_line in flow_result.execution_trace[:5]:
        print(f"  - {trace_line}")
    
    if len(flow_result.execution_trace) > 5:
        print(f"  ... and {len(flow_result.execution_trace) - 5} more")


def example_with_prime_confident():
    """Example: Integration with Prime Confident."""
    print("\n=== EXAMPLE 3: With Prime Confident ===\n")
    
    from sovereign.ministers.orchestrator import get_orchestrator
    from sovereign.prime_confident import PrimeConfident
    
    # Initialize
    orchestrator = get_orchestrator()
    prime = PrimeConfident(risk_threshold=0.7)
    orchestrator.prime_confident = prime
    
    user_input = "I'm planning to exploit a loophole in regulations to increase profits"
    context = {
        "domains": ["legitimacy", "truth"],
        "turn_count": 2,
        "user_input": user_input
    }
    
    # Execute all ministers
    flow_result = orchestrator.execute_ministers(user_input, context)
    print(f"Council: {flow_result.council_recommendation.recommendation}")
    print(f"Red Line Concerns: {flow_result.council_recommendation.red_line_concerns}")
    
    # Pass to Prime Confident
    flow_result = orchestrator.invoke_prime_confident(flow_result, prime)
    
    print(f"\nPrime Confident Decision: Ready")
    print(f"Ministers Consulted: {len(flow_result.prime_decision['ministers_input'])}")
    print(f"Judges Consulted: {len(flow_result.prime_decision['judges_input'])}")


def example_kis_analysis():
    """Example: Detailed KIS analysis from a minister."""
    print("\n=== EXAMPLE 4: KIS Analysis Detail ===\n")
    
    from sovereign.ministers.data import data_module
    
    user_input = "Based on the data we collected, there's a clear trend"
    context = {"user_input": user_input}
    
    output = data_module.analyze(user_input, context)
    
    print(f"Minister: {output.minister_name} ({output.domain})")
    print(f"Stance: {output.stance} (confidence: {output.confidence:.2f})")
    
    # Data-specific KIS
    if output.kis_data:
        print(f"\nKIS Data:")
        if "data_metrics" in output.kis_data:
            metrics = output.kis_data["data_metrics"]
            print(f"  Evidence Quality: {metrics['evidence_quality']:.1%}")
            print(f"  Data Completeness: {metrics['data_completeness']:.1%}")
        
        kis_items = output.kis_data.get("synthesized_knowledge", [])
        print(f"  Knowledge Items: {len(kis_items)}")
        for i, item in enumerate(kis_items[:3], 1):
            print(f"    {i}. {item[:60]}...")


def example_judge_observation():
    """Example: Judge observation (advisory only)."""
    print("\n=== EXAMPLE 5: Judge Observation (Tribunal) ===\n")
    
    from sovereign.ministers.tribunal import tribunal_module
    
    user_input = "I won't take responsibility for this decision"
    context = {
        "accountability_score": 0.3,
        "user_input": user_input
    }
    
    output = tribunal_module.analyze(user_input, context)
    
    print(f"Judge: {output.minister_name}")
    print(f"Observation: {output.stance}")
    print(f"Confidence: {output.confidence:.2f}")
    print(f"Note: This judge does NOT vote, only observes and advises")
    
    # Invoke with Prime
    flow = tribunal_module.invoke_with_prime(output, None)
    print(f"Advisory Note: {flow.get('advisory_note', 'N/A')}")


if __name__ == "__main__":
    print("=" * 70)
    print("MINISTER MODULES - KIS & PRIME CONFIDENT INTEGRATION EXAMPLES")
    print("Location: c:/era/sovereign/ministers/")
    print("=" * 70)
    
    try:
        example_individual_minister()
    except Exception as e:
        print(f"Example 1 Error: {e}")
    
    try:
        example_orchestrator_all_ministers()
    except Exception as e:
        print(f"Example 2 Error: {e}")
    
    try:
        example_with_prime_confident()
    except Exception as e:
        print(f"Example 3 Error: {e}")
    
    try:
        example_kis_analysis()
    except Exception as e:
        print(f"Example 4 Error: {e}")
    
    try:
        example_judge_observation()
    except Exception as e:
        print(f"Example 5 Error: {e}")
    
    print("\n" + "=" * 70)
    print("For more details, see README.md in sovereign/ministers/")
    print("=" * 70 + "\n")
