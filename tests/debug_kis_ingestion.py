#!/usr/bin/env python
"""Debug why KIS guidance is empty in doctrines"""
import json
import sys
sys.path.insert(0, 'C:\\era')

# Load the doctrines
with open('ingestion/v2/rag_storage/16-05-2021-070111The-Richest-Man-in-Babylon/02_doctrine.json') as f:
    doctrines = json.load(f)

# Check first few doctrines
print('First 3 doctrines:')
for i, doc in enumerate(doctrines[:3]):
    ch_title = doc.get('chapter_title', 'N/A')[:30] if doc.get('chapter_title') else 'N/A'
    print(f"  {i+1}. Ch {doc.get('chapter_index')}: {ch_title}")
    print(f"     domains: {doc.get('domains')}")
    items = sum(len(doc.get(field, [])) for field in ('principles', 'rules', 'claims', 'warnings'))
    print(f"     total items: {items}")
    kis_items = doc.get('kis_guidance', [])
    print(f"     kis_guidance items: {len(kis_items)}")
    if kis_items and isinstance(kis_items, list):
        for j, item in enumerate(kis_items[:1]):
            print(f"       - {str(item)[:60]}...")
    print()

# Now test KIS synthesis for the first doctrine
print("\n[TEST] Running KIS synthesis on first doctrine:")
from ingestion.v2.src.ingestion_kis_enhancer import IngestionKISEnhancer, IngestionKISContext

enhancer = IngestionKISEnhancer(knowledge_base_path="data/ministers")
doc = doctrines[0]

domains = doc.get("domains", [])
minister_domain = domains[0] if domains else "general"
print(f"Minister domain: {minister_domain}")

# Get first item for excerpt
doctrine_excerpt = ""
for field in ("principles", "rules", "claims", "warnings"):
    items = doc.get(field, [])
    if items:
        doctrine_excerpt = str(items[0])[:300]
        break

print(f"Doctrine excerpt: {doctrine_excerpt[:70]}...")

# Create context and enhance
context = IngestionKISContext(
    chapter_title=doc.get("chapter_title", "Unknown"),
    minister_domain=minister_domain,
    doctrine_excerpt=doctrine_excerpt,
    ingestion_job_id=f"test_ch_{doc.get('chapter_index')}"
)

context = enhancer.enhance_aggregation_stage(context, max_related_items=3)
print(f"\nKIS synthesis returned {len(context.kis_synthesis or [])} items")
if context.kis_synthesis:
    for i, item in enumerate(context.kis_synthesis[:2], 1):
        print(f"  {i}. {str(item)[:70]}...")
