#!/usr/bin/env python3
"""Test deepseek model with doctrine extraction prompt."""
import requests
import json

# Sample text
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
"""

# Doctrine extraction prompt
SYSTEM_PROMPT = """You are an operational doctrine extraction engine.

Your task is to EXTRACT actionable operational guidance from text.
Not to quote verbatim, but to ABSTRACT principles, rules, decision criteria, warnings, and claims.

MANDATORY OUTPUT REQUIREMENTS:
- You MUST include a field called "domains".
- "domains" MUST be a list of 1 to 3 items.
- Each domain MUST be chosen ONLY from the list below.
- If no domain applies, choose the closest applicable domain.

ALLOWED DOMAINS (EXACT STRINGS):
adaptation, base, conflict, constraints, data, diplomacy, discipline, executor, legitimacy, optionality, power, psychology, registry, risk, strategy, technology, timing, truth

EXTRACTION GUIDELINES:
1. A PRINCIPLE is a fundamental truth, maxim, or foundation for action (e.g., "reputation is built over time").
2. A RULE is a prescriptive action, constraint, or decision criterion (e.g., "never engage without understanding opponent intentions").
3. A CLAIM is a factual assertion made by the text (e.g., "wealth compounds over time").
4. A WARNING is a cautionary statement or risk indicator (e.g., "acting without patience leads to failure").

EXTRACTION RULES:
- Generalize language: convert specific examples into abstract principles.
- DO NOT quote sentences verbatim; paraphrase into normalized language.
- Focus on *operational content*: advice, decision rules, risk factors, foundational beliefs.

WHEN TO EXTRACT:
- ANY clear guidance, advice, lesson, or principle = EXTRACT.
- ANY operational decision rule or constraint = EXTRACT.
- ANY risk, warning, or caution = EXTRACT.

MINIMIZE EMPTY FIELDS:
- If the text contains ANY actionable content, extract SOMETHING into each field.
- Prefer over-extraction to under-extraction.

Return ONLY valid JSON. Do not include commentary."""

user_prompt = f"""RETURN JSON WITH THIS EXACT STRUCTURE:

{{
    "domains": [],
    "principles": [],
    "rules": [],
    "claims": [],
    "warnings": []
}}

CHAPTER INDEX: 1

TEXT (for analysis only — DO NOT QUOTE):
--------------------------------------
{sample_text}
--------------------------------------

INSTRUCTIONS:
1. Select 1–3 applicable DOMAINS from the provided list.
2. Extract actionable operational content: ANY principles, rules, decision criteria, warnings, or claims.
3. Generalize: convert specific examples into abstract, normalized language.
4. Do not quote; paraphrase and abstract.

If the text has NO operational content, return minimal but valid JSON with at least domains populated.
"""

print("=" * 70)
print("TESTING DEEPSEEK MODEL FOR DOCTRINE EXTRACTION")
print("=" * 70)

try:
    # Test deepseek
    model = "huihui_ai/deepseek-r1-abliterated:8b"
    print(f"\nTesting model: {model}")
    
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "format": "json",
    }
    
    response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
    response.raise_for_status()
    
    raw_response = response.json().get("response", "").strip()
    print(f"\nRaw response length: {len(raw_response)}")
    
    result = json.loads(raw_response)
    print("\nExtraction Result:")
    print(json.dumps(result, indent=2))
    
    # Validation
    total = sum(len(result.get(k, [])) for k in ["principles", "rules", "claims", "warnings"])
    print(f"\nTotal items extracted: {total}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
