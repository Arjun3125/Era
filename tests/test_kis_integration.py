#!/usr/bin/env python
"""Test KIS integration independently"""
import sys
sys.path.insert(0, 'C:\\era')

from ml.kis.knowledge_integration_system import KnowledgeIntegrationSystem, KISRequest
from ingestion.v2.src.ingestion_kis_enhancer import IngestionKISEnhancer, IngestionKISContext

print("[TEST] Initializing KIS enhancer...")
enhancer = IngestionKISEnhancer(knowledge_base_path="data/ministers")
print("[OK] KIS enhancer created")

# Test 1: Create a context
print("\n[TEST] Creating KIS context...")
context = IngestionKISContext(
    chapter_title="Financial Wisdom",
    minister_domain="wealth",
    doctrine_excerpt="Save first, spend second. Financial buffers are critical.",
    ingestion_job_id="test_001"
)
print(f"[OK] Context created: {context.ingestion_job_id}")

# Test 2: Enhance with KIS
print("\n[TEST] Running KIS synthesis...")
try:
    context = enhancer.enhance_aggregation_stage(context, max_related_items=3)
    print(f"[OK] KIS synthesis complete")
    print(f"  kis_synthesis items: {len(context.kis_synthesis or [])}")
    print(f"  kis_context keys: {list((context.kis_context or {}).keys())}")

    if context.kis_synthesis:
        print("\n[OK] KIS returned knowledge items:")
        for i, item in enumerate(context.kis_synthesis[:2], 1):
            print(f"     {i}. {str(item)[:100]}...")
    else:
        print("\n[WARN] No KIS synthesis returned")
except Exception as e:
    print(f"[ERROR] KIS synthesis failed: {e}")
    import traceback
    traceback.print_exc()

print("\n[TEST] Complete!")
