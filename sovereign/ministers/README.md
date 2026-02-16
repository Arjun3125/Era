"""
MINISTER MODULES INTEGRATION GUIDE

Location: c:\era\sovereign\ministers\

This directory contains individual Python modules for each minister, with KIS generation
and Prime Confident flow integration.

STRUCTURE:
- __init__.py: Base MinisterModule class and factory functions
- {domain}.py: Individual minister modules (19 voting + 1 judge)
- orchestrator.py: Main orchestrator for coordinating all ministers

USAGE:

1. Import and use individual minister:
   
   from sovereign.ministers.adaptation import adaptation_module
   
   output = adaptation_module.analyze(user_input, context)
   kis_data = output.kis_data  # Domain-specific knowledge
   flow = adaptation_module.invoke_with_prime(output, prime_confident)

2. Use orchestrator to run all ministers:
   
   from sovereign.ministers.orchestrator import get_orchestrator
   
   orchestrator = get_orchestrator(llm=llm)
   flow_result = orchestrator.execute_ministers(user_input, context)
   
   # Access results:
   flow_result.minister_outputs  # Dict of all minister positions
   flow_result.judge_observations  # Advisory judge (Tribunal)
   flow_result.council_recommendation  # Aggregated council vote
   flow_result.kis_summary  # KIS statistics
   flow_result.execution_trace  # Full execution trace

3. Flow with Prime Confident:
   
   from sovereign.prime_confident import PrimeConfident
   
   prime = PrimeConfident()
   orchestrator.prime_confident = prime
   
   flow_result = orchestrator.execute_ministers(user_input, context)
   flow_result = orchestrator.invoke_prime_confident(flow_result, prime)
   
   # Prime decision is in flow_result.prime_decision

MINISTER MODULES (19 Voting):
- adaptation: Change and evolution detection
- conflict: Adversarial dynamics assessment
- diplomacy: Stakeholder relationship impact
- data: Evidence-based reasoning quality
- discipline: Consistency and principle adherence
- grand_strategist: Long-term vision alignment
- intelligence: Information quality and gaps
- timing: Action timing evaluation
- risk: Downside scenario identification
- power: Capability and leverage assessment
- psychology: Human factors and emotion
- technology: Technical feasibility
- legitimacy: Values and authority alignment
- truth: Reality and deception detection
- narrative: Story coherence evaluation
- sovereign: Self-determination clarity
- optionality: Strategic flexibility preservation
- risk_resources: Scarcity and resource management
- war_mode: Aggressive action scenarios

JUDGE MODULES (1 Advisory):
- tribunal: Accountability and consequences (observes, doesn't vote)

KEY FEATURES:

✓ Domain-specific KIS generation for each minister
✓ Automatic caching of KIS results
✓ Full execution tracing and audit trail
✓ Exception handling per minister (one failure doesn't break flow)
✓ Advisory-only judges (Tribunal)
✓ Prime Confident flow integration
✓ Parallel execution ready (asyncio compatible)

KIS INTEGRATION:
Each minister module calls synthesize_knowledge() for their domain, capturing:
- Relevant knowledge items
- Domain-specific indicators
- Context-aware metrics
- Cached for performance

PRIME CONFIDENT FLOW:
invoke_with_prime() packages each minister's position with KIS data for
Prime Confident's final decision layer, which includes:
- Emotional distortion detection
- Pattern recurrence identification
- Doctrine constraint enforcement

IMPORTS:
All imports are absolute and reference:
- persona.knowledge_engine (for KIS generation)
- persona.ministers (for minister classes)
- persona.council (for council aggregation)
- persona.trace (for execution tracing)
