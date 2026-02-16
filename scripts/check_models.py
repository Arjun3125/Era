#!/usr/bin/env python3
"""Diagnostic: check which model the pipeline is actually using for doctrine extraction."""
import sys, importlib.util, os
sys.path.insert(0, r"c:\era\ingestion\v2\src")

# Load config directly
spec = importlib.util.spec_from_file_location("config", r"c:\era\ingestion\v2\src\config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

DEFAULT_EXTRACT_MODEL = config.DEFAULT_EXTRACT_MODEL
DEFAULT_DEEPSEEK_MODEL = config.DEFAULT_DEEPSEEK_MODEL
DEFAULT_EMBED_MODEL = config.DEFAULT_EMBED_MODEL

print("=" * 70)
print("MODEL CONFIGURATION CHECK")
print("=" * 70)
print(f"DEFAULT_EXTRACT_MODEL: {DEFAULT_EXTRACT_MODEL}")
print(f"DEFAULT_DEEPSEEK_MODEL: {DEFAULT_DEEPSEEK_MODEL}")
print(f"DEFAULT_EMBED_MODEL: {DEFAULT_EMBED_MODEL}")
print()

print(f"Pipeline will use:")
print(f"  Extractor model: {DEFAULT_EXTRACT_MODEL}")
print(f"  Doctrine model: {DEFAULT_DEEPSEEK_MODEL}")
print(f"  Embed model: {DEFAULT_EMBED_MODEL}")
print()

# Summary of DEFAULT_DEEPSEEK_MODEL
print(f"Doctrine model for extraction: {DEFAULT_DEEPSEEK_MODEL}")
if "llama" in DEFAULT_DEEPSEEK_MODEL.lower():
    print(f"✓ Good: Using instruction-following model (llama3.1)")
else:
    print(f"✗ Issue: Model might not be appropriate for structured extraction")
