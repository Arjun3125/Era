#!/usr/bin/env python3
"""Test script to verify improved doctrine extraction prompt."""

import json
import os
import sys
import requests

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), "..", "ingestion", "v2", "src")
sys.path.insert(0, src_path)

# Import with direct relative path handling
import importlib.util
spec = importlib.util.spec_from_file_location("config", os.path.join(src_path, "config.py"))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

SYSTEM_PROMPT_DOCTRINE = config.SYSTEM_PROMPT_DOCTRINE


def test_extraction():
    """Test doctrine extraction with the improved prompt on sample text."""
    
    # Sample text from a business/finance book (similar to Richest Man in Babylon)
    sample_text = """
    The secret to building wealth is to pay yourself first. Before paying any bills 
    or making any purchases, set aside a portion of your income for investment. This 
    principle ensures that your wealth grows consistently over time. Many people fail 
    to accumulate wealth because they treat saving as an afterthought, spending money 
    on immediate gratification first.
    
    A second critical rule is to diversify your income sources. Relying on a single 
    job or business is risky. Wealthy individuals develop multiple streams of income - 
    from investments, side businesses, rental properties, and other ventures. This 
    approach protects you if one income source dries up.
    
    Never confuse income with wealth. Income is the money you earn; wealth is what 
    you keep and grow. Many high-income earners remain poor because they spend all 
    their earnings. The path to wealth requires discipline to spend less than you earn.
    
    Compound interest is the eighth wonder of the world. When you reinvest your earnings 
    and let them accumulate over time, the growth accelerates exponentially. Starting 
    early is crucial - even modest investments grow substantially over decades.
    
    Warning: Debt is the enemy of wealth building. Consumer debt especially - credit 
    cards, auto loans for luxury items - consumes your future earnings and prevents 
    you from accumulating capital. Avoid debt except for investments that generate 
    returns exceeding the interest rate.
    """
    
    print("=" * 70)
    print("TESTING IMPROVED DOCTRINE EXTRACTION PROMPT")
    print("=" * 70)
    print(f"\nOriginal System Prompt (first 500 chars):\n{SYSTEM_PROMPT_DOCTRINE[:500]}\n")
    
    # Create a minimal user prompt following the doctrine extraction format
    json_skeleton = (
        '{\n'
        '    "domains": [],\n'
        '    "principles": [],\n'
        '    "rules": [],\n'
        '    "claims": [],\n'
        '    "warnings": []\n'
        '}'
    )
    
    user_prompt = (
        "RETURN JSON WITH THIS EXACT STRUCTURE:\n\n"
        + json_skeleton
        + "\n\nCHAPTER INDEX: 1\n\nTEXT (for analysis only — DO NOT QUOTE):\n"
        + "--------------------------------------\n"
        + sample_text[:8000]
        + "\n--------------------------------------\n\n"
        + "INSTRUCTIONS:\n"
        + "1. Select 1–3 applicable DOMAINS from the provided list.\n"
        + "2. Extract actionable operational content: ANY principles, rules, decision criteria, warnings, or claims.\n"
        + "3. Generalize: convert specific examples into abstract, normalized language.\n"
        + "4. Do not quote; paraphrase and abstract.\n\n"
        + "EXTRACTION REQUIREMENTS:\n"
        + "- IF the text contains operational guidance (advice, lessons, decision rules, warnings), EXTRACT IT.\n"
        + "- If any field seems empty, infer from context (e.g., infer rules from principles).\n"
        + "- PREFERENCE: Over-extraction is better than under-extraction.\n"
        + "- MINIMUM TARGET: If guidance exists, aim for at least 1–2 items per field (principles, rules, claims, warnings).\n"
        + "- DOMAINS MUST NOT BE EMPTY.\n\n"
        + "EXAMPLES OF OPERATIONAL CONTENT:\n"
        + "- [Financial book] 'Save before you spend' → principle; 'Never spend principal' → rule; 'Compound interest builds wealth' → claim.\n"
        + "- [Management text] 'Delegate effectively' → principle; 'Set clear expectations' → rule; 'Unclear delegation causes failure' → warning.\n"
        + "- [Narrative with lessons] ANY learning, advice, or cautionary element = extract.\n\n"
        + "If the text has NO operational content, return minimal but valid JSON with at least domains populated.\n"
    )
    
    print(f"Sample Text (truncated):\n{sample_text[:300]}...\n")
    print("=" * 70)
    print("CALLING OLLAMA WITH IMPROVED PROMPT...")
    print("=" * 70)
    
    try:
        # Call Ollama directly via HTTP
        parse_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.1:8b-instruct-q4_0",
            "system": SYSTEM_PROMPT_DOCTRINE,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
        }
        
        print("\nCalling Ollama /api/generate endpoint...")
        response = requests.post(parse_url, json=payload, timeout=120)
        response.raise_for_status()
        
        response_data = response.json()
        raw_response = response_data.get("response", "").strip()
        
        # Try to parse as JSON
        result = json.loads(raw_response)
        
        print("\nEXTRACTION RESULT:")
        print(json.dumps(result, indent=2))
        
        # Quick validation
        if result.get("domains"):
            print(f"\n[GOOD] Domains extracted: {result['domains']}")
        else:
            print("\n[ISSUE] No domains extracted")
            
        for field in ["principles", "rules", "claims", "warnings"]:
            count = len(result.get(field, []))
            if count > 0:
                print(f"[GOOD] {field}: {count} items")
            else:
                print(f"[ISSUE] {field}: empty (0 items)")
        
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to Ollama at http://localhost:11434")
        print("Make sure Ollama is running: ollama serve")
    except Exception as e:
        print(f"\nERROR during extraction: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_extraction()
