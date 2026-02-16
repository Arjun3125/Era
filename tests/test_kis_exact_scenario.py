#!/usr/bin/env python
"""Replicate exact ingestion scenario to find KIS issue"""
import json
import sys
import os
sys.path.insert(0, 'C:\\era')

from ingestion.v2.src.ingestion_kis_enhancer import IngestionKISEnhancer, IngestionKISContext

print("[TEST] Initializing KIS enhancer with resume=False scenario...")

# Simulate ingestion state
book_id = "16-05-2021-070111The-Richest-Man-in-Babylon"
storage = f"ingestion/v2/rag_storage/{book_id}"

# Load pre-enhanced doctrines
with open(os.path.join(storage, "02_doctrine.json")) as f:
    doctrines = json.load(f)

print(f"Loaded {len(doctrines)} doctrines")

# Try to initialize enhancer EXACTLY as the pipeline does
try:
    kis_enhancer = IngestionKISEnhancer(knowledge_base_path="data/ministers")
    print("[OK] KIS enhancer initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Simulate the enhancement loop for first 3 doctrines
ingestion_job_outcomes = {}
for idx, doctrine in enumerate(doctrines[:3], start=1):
    print(f"\n[CH {idx}] Processing...")
    try:
        domains = doctrine.get("domains", [])
        minister_domain = domains[0] if domains else "general"
        
        # Get first 300 chars 
        doctrine_excerpt = ""
        for field in ("principles", "rules", "claims", "warnings"):
            items = doctrine.get(field, [])
            if items:
                doctrine_excerpt = str(items[0])[:300]
                break
        
        # Create context
        job_id = f"ingest_{book_id}_{idx}"
        kis_context = IngestionKISContext(
            chapter_title=doctrine.get("chapter_title", f"Chapter {idx}"),
            minister_domain=minister_domain,
            doctrine_excerpt=doctrine_excerpt,
            ingestion_job_id=job_id
        )
        
        print(f"  Created context: domain={minister_domain}")
        
        # Enhance with KIS
        print(f"  Calling enhance_aggregation_stage...")
        kis_context = kis_enhancer.enhance_aggregation_stage(
            kis_context,
            max_related_items=3
        )
        
        print(f"  KIS synthesis returned: {len(kis_context.kis_synthesis or [])} items")
        
        # Add to doctrine (exactly as pipeline does)
        if kis_context.kis_synthesis:
            doctrine["kis_guidance"] = kis_context.kis_synthesis
            doctrine["kis_context"] = kis_context.kis_context
            print(f"  ✓ Added kis_guidance to doctrine")
        else:
            print(f"  ✗ kis_synthesis was empty!")
            doctrine["kis_guidance"] = kis_context.kis_synthesis or []
            doctrine["kis_context"] = kis_context.kis_context
        
        ingestion_job_outcomes[job_id] = {
            "kis_context": kis_context,
            "doctrine_idx": idx,
        }
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

print(f"\n[FINAL] Ingestion job outcomes: {len(ingestion_job_outcomes)}")
for job_id, data in ingestion_job_outcomes.items():
    print(f"  {job_id}: {len(data['kis_context'].kis_synthesis or [])} items")
