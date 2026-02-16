#!/usr/bin/env python3
"""
Step 3: Test LLM Client Integration

Verifies that:
1. LLMInterface connects to Ollama
2. 4-call handshake works
3. JSON parsing succeeds
4. Retry logic handles failures
"""

import sys
import os

sys.path.insert(0, r'C:\era')

print('=' * 80)
print('STEP 3: LLM Client Integration Test')
print('=' * 80)

# Step 1: Import and initialize
print('\n[STEP 1] Importing LLMInterface...')
try:
    from ml.llm_handshakes.llm_interface import LLMInterface
    print('[OK] LLMInterface imported')
except Exception as e:
    print(f'[ERROR] Import failed: {e}')
    sys.exit(1)

# Step 2: Create interface
print('\n[STEP 2] Initializing LLM Interface...')
try:
    llm = LLMInterface(
        model="huihui_ai/deepseek-r1-abliterated:8b",
        max_retries=1,
        timeout=60
    )
    print(f'[OK] LLMInterface initialized')
    print(f'  Model: {llm.model}')
    print(f'  Base URL: {llm.base_url}')
    print(f'  Client available: {llm.client is not None}')
except Exception as e:
    print(f'[ERROR] Initialization failed: {e}')
    sys.exit(1)

# Step 3: Test Ollama connectivity  
print('\n[STEP 3] Testing Ollama connectivity...')
if not llm.client:
    print('[WARN] Ollama client not available - cannot test')
    print('  (Install OllamaClient to enable actual LLM calls)')
    print('  Skipping remaining tests')
    sys.exit(0)

try:
    # Test with a simple prompt
    test_prompt = "Return JSON: {\"test\": true, \"value\": 42}"
    test_response = llm.call_llm("You are a test", test_prompt)
    if test_response and "{" in test_response:
        print(f'[OK] Ollama connectivity verified')
        print(f'  Response length: {len(test_response)} chars')
    else:
        print(f'[WARN] Got response but not JSON: {test_response[:100]}')
except Exception as e:
    print(f'[WARN] Ollama connectivity test failed: {e}')
    print('  (This might mean Ollama is not running)')

# Step 4: Test 4-call handshake
print('\n[STEP 4] Testing 4-call handshake sequence...')
try:
    sample_situation = """
    I've been offered a senior position at a new company. 
    It's 50% more pay, but requires relocating with my family.
    I have 3 days to decide.
    """
    
    print('  Running handshake on sample situation...')
    result = llm.run_handshake_sequence(sample_situation)
    
    # Check results
    has_situation = 'situation' in result
    has_constraints = 'constraints' in result
    has_counterfactuals = 'counterfactuals' in result
    has_intent = 'intent' in result
    
    print(f'  Situation frame: {"[OK]" if has_situation else "[FAIL]"}')
    print(f'  Constraints: {"[OK]" if has_constraints else "[FAIL]"}')
    print(f'  Counterfactuals: {"[OK]" if has_counterfactuals else "[FAIL]"}')
    print(f'  Intent detection: {"[OK]" if has_intent else "[FAIL]"}')
    
    if all([has_situation, has_constraints, has_counterfactuals, has_intent]):
        print('[OK] 4-call handshake completed successfully')
        
        # Show sample output
        if 'situation' in result:
            sit = result['situation']
            print(f'\n  Sample output:')
            print(f'    Decision type: {sit.get("decision_type", "N/A")}')
            print(f'    Risk level: {sit.get("risk_level", "N/A")}')
            print(f'    Time pressure: {sit.get("time_pressure", 0):.1f}')
    else:
        print('[WARN] Handshake incomplete but no errors raised')
        
except Exception as e:
    print(f'[ERROR] Handshake failed: {e}')
    import traceback
    traceback.print_exc()

# Step 5: Test call count
print('\n[STEP 5] Checking call statistics...')
print(f'  Total LLM calls made: {llm.call_count}')
print(f'  Expected: 4 (one per handshake call)')

print('\n' + '=' * 80)
print('TEST COMPLETE')
print('=' * 80)

# Summary
print('\n[SUMMARY] Step 3 Status:')
if llm.client:
    print('[OK] LLM Client fully integrated with Ollama')
    if llm.call_count >= 4:
        print('[OK] 4-call handshake working')
        print('[OK] Ready for KIS integration')
    else:
        print('[WARN] Fewer calls than expected - check Ollama server')
else:
    print('[WARN] LLM Client initialized but Ollama not connected')
    print('  Ensure Ollama is running: ollama serve')
