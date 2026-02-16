import sys, os, json, shutil
from pathlib import Path

# Clean
storage = Path(r'C:\era\ingestion\v2\rag_storage\test_kis_debug')
if storage.exists():
    shutil.rmtree(storage)

# Minimal test - just test the KIS enhancement directly
sys.path.insert(0, r'C:\era')

from ingestion.v2.src.ingestion_kis_enhancer import IngestionKISContext, IngestionKISEnhancer
from ml.kis.knowledge_integration_system import KnowledgeIntegrationSystem

print('[TEST] Initializing KIS enhancer...')
enhancer = IngestionKISEnhancer(knowledge_base_path="data/ministers")

# Create a dummy doctrine
dummy_doctrine = {
    "chapter_index": 1,
    "chapter_title": "Intro",
    "domains": ["finance"],
    "principles": ["Save first"],
    "rules": ["Budget your income"],
    "claims": ["Saving builds wealth"],
    "warnings": ["Overspending is risky"]
}

print('[TEST] Creating KIS context...')
context = IngestionKISContext(
    chapter_title="Intro",
    minister_domain="finance",
    doctrine_excerpt="Save first",
    ingestion_job_id="test_1"
)

print('[TEST] Enhancing with KIS...')
context = enhancer.enhance_aggregation_stage(context, max_related_items=3)

print(f'[TEST] KIS synthesis: {len(context.kis_synthesis)} items')
print(f'[TEST] Context keys: {list(context.__dict__.keys())}')

# Try adding to doctrine
if context.kis_synthesis:
    dummy_doctrine['kis_guidance'] = context.kis_synthesis
    print(f'[TEST] Added kis_guidance to doctrine')
    print(f'[TEST] Doctrine now has: {list(dummy_doctrine.keys())}')
    print(f'[TEST] kis_guidance value type: {type(dummy_doctrine["kis_guidance"])}')
else:
    print('[TEST] No KIS synthesis returned!')
    
# Test JSON serialization
print('[TEST] Testing JSON serialization...')
json_str = json.dumps(dummy_doctrine)
from_json = json.loads(json_str)
if 'kis_guidance' in from_json:
    print(f'[TEST] ✓ kis_guidance survived JSON roundtrip')
else:
    print(f'[TEST] ✗ kis_guidance LOST in JSON roundtrip!')
    print(f'[TEST] Keys after JSON: {list(from_json.keys())}')
