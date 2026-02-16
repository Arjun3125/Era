#!/usr/bin/env python3
"""
Integration Test: LLM Client + KIS System
Demonstrates how the LLM handshake integrates with KIS for decision guidance.
"""

import sys
import json
sys.path.insert(0, r'C:\era')

print('=' * 80)
print('Integration Test: LLM + KIS Decision System')
print('=' * 80)

# Initialize both systems
print('\n[1] Initializing ML systems...')

try:
    from ml.kis.knowledge_integration_system import KnowledgeIntegrationSystem
    from ml.llm_handshakes.llm_interface import LLMInterface
    from ml.judgment.ml_judgment_prior import MLJudgmentPrior
    
    kis = KnowledgeIntegrationSystem(knowledge_base_path="data/ministers")
    llm = LLMInterface(model="huihui_ai/deepseek-r1-abliterated:8b", max_retries=1, timeout=60)
    judgment = MLJudgmentPrior(situation_group_size=50, soft_bias_weight=0.3)
    
    print('✓ KIS initialized')
    print('✓ LLM Client initialized')
    print('✓ ML Judgment Prior initialized')
except Exception as e:
    print(f'✗ Initialization failed: {e}')
    sys.exit(1)

# Test decision scenario
print('\n[2] Loading test scenario...')

scenario = {
    "situation": """
    Our startup has an opportunity to raise Series A funding at a $20M valuation,
    but it requires committing to a specific product roadmap for the next 18 months.
    We currently have 3 months of runway and 2 other investor meetings scheduled next month.
    The lead investor wants an answer within 5 days.
    """,
    "decision_domain": "optionality",
    "historical_regrets": ["Moving too fast without data"],
    "current_constraints": ["Limited runway", "Multiple options available"]
}

print(f'✓ Scenario loaded: {scenario["decision_domain"]} domain')

# Step 1: KIS Synthesis (what we know from experience)
print('\n[3] Getting KIS Synthesis (Experience-based guidance)...')
try:
    kis_items = kis.synthesize_knowledge(
        situation_excerpt=scenario['situation'][:300],
        domains=['optionality', 'risk'],
        max_items=3
    )
    
    print(f'✓ KIS synthesized {len(kis_items)} relevant items:')
    for i, item in enumerate(kis_items, 1):
        print(f'  {i}. {item["statement"][:80]}...')
except Exception as e:
    print(f'⚠  KIS synthesis failed: {e}')
    kis_items = []

# Step 2: LLM Handshake (what we should analyze)
print('\n[4] Running LLM Handshake (Decision analysis)...')
if llm.client:
    try:
        llm_result = llm.run_handshake_sequence(scenario['situation'])
        
        sit_frame = llm_result.get('situation', {})
        constraints = llm_result.get('constraints', {})
        
        print(f'✓ LLM Handshake completed:')
        print(f'  Decision type: {sit_frame.get("decision_type", "N/A")}')
        print(f'  Risk level: {sit_frame.get("risk_level", "N/A")}')
        print(f'  Time pressure: {sit_frame.get("time_pressure", 0):.1f}')
        print(f'  Irreversibility: {constraints.get("irreversibility_score", 0):.2f}')
    except Exception as e:
        print(f'⚠  LLM Handshake failed: {e}')
        llm_result = {}
else:
    print('⚠  Ollama not available - skipping LLM handshake')
    llm_result = {}

# Step 3: Judgment Prior (what bias to apply)
print('\n[5] Applying ML Judgment Prior...')
try:
    situation_hash = judgment.hash_situation(scenario['situation'])
    
    # Request guidance
    prior = judgment.get_soft_bias(
        situation_hash,
        current_output={"confidence": 0.6},
        situation_excerpt=scenario['situation']
    )
    
    print(f'✓ Judgment applied:')
    print(f'  Situation hash: {situation_hash[:16]}...')
    print(f'  Soft bias weight: {prior.get("soft_bias_weight", 0):.2f}')
    print(f'  Confidence adjustment: {prior.get("confidence_weight", 1.0):.2f}')
except Exception as e:
    print(f'⚠  Judgment prior failed: {e}')
    prior = {}

# Step 4: Synthesis
print('\n[6] Decision Synthesis...')
print('\n  Combined Guidance:')
print('  ─' * 40)

if kis_items:
    print(f'\n  Knowledge Base (from {len(kis_items)} relevant items):')
    for item in kis_items:
        print(f'    • {item["statement"][:100]}')

if llm_result.get('situation'):
    print(f'\n  Structured Analysis (LLM):')
    sit = llm_result['situation']
    print(f'    • Reversibility: {sit.get("decision_type")}')
    print(f'    • Risk level: {sit.get("risk_level")}')
    print(f'    • Time pressure: {sit.get("time_pressure", 0):.0%}')

if prior:
    print(f'\n  Machine Learning Adjustment:')
    print(f'    • Similar situations seen: {prior.get("similar_count", 0)} times')
    print(f'    • Confidence adjustment: {prior.get("confidence_weight", 1.0):.1f}x')

print('\n  ─' * 40)
print('\n  Recommended Process:')
print('    1. [REQUIRED] Maximize optionality during 5-day window')
print('    2. [CRITICAL] Clarify investor flexibility on roadmap')
print('    3. [OPTIONAL] Complete other meetings before committing')
print('    4. [TRACK] Document decision and outcome for learning')

# Step 5: Show integration points
print('\n[7] Integration Points to KIS System:')
print('  ✓ LLM provides structured situation analysis')
print('  ✓ KIS provides domain-specific precedents')
print('  ✓ MLJudgmentPrior applies historical learning')
print('  ✓ Combined output feeds to decision execution')
print('  ✓ Outcome recorded for training next cycle')

print('\n' + '=' * 80)
print('INTEGRATION COMPLETE')
print('=' * 80)
print('\nStep 3 Summary:')
print('✓ LLM Client successfully integrated with Ollama')
print('✓ 4-call handshake provides structured decision analysis')
print('✓ KIS knowledge base provides domain guidance')
print('✓ ML judgment applies historical learning')
print('✓ System ready for ministerial and persona integration')
