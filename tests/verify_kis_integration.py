#!/usr/bin/env python3
"""Verify KIS enhancement is saved to doctrines"""
import sys, os, json, shutil
from pathlib import Path

sys.path.insert(0, r'C:\era')

# Clean
test_storage = Path(r'C:\era\ingestion\v2\rag_storage\kis_verification_test')
if test_storage.exists():
    shutil.rmtree(test_storage)

print('[TEST] Step 1: Run ingestion...')
from ingestion.v2.src.ingest_pipeline import run_full_ingest_with_resume
book_path = r'C:\era\data\books\16-05-2021-070111The-Richest-Man-in-Babylon.pdf'

try:
    run_full_ingest_with_resume(book_path, resume=False)
except Exception as e:
    print(f'[ERROR] Ingestion failed: {e}')
    sys.exit(1)

# The ingestion uses its own storage path based on book_id
# So find where it actually stored the doctrines
import glob
doctrine_files = sorted(
    glob.glob(r'C:\era\ingestion\v2\rag_storage\*/02_doctrine.json'),
    key=os.path.getmtime,
    reverse=True
)

if not doctrine_files:
    print('[ERROR] No doctrine files found')
    sys.exit(1)

doc_file = doctrine_files[0]
print(f'[TEST] Step 2: Check doctrines at {Path(doc_file).parent.name}')

with open(doc_file) as f:
    doctrines = json.load(f)

with_kis = sum(1 for d in doctrines if 'kis_guidance' in d)
total = len(doctrines)

print(f'[TEST] Step 3: Verify KIS guidance')
print(f'  Total doctrines: {total}')
print(f'  With kis_guidance: {with_kis}')
print(f'  Rate: {100*with_kis/total:.1f}%')

if with_kis > 0:
    print(f'\n[SUCCESS] KIS guidance is being saved!')
    for d in doctrines:
        if 'kis_guidance' in d:
            ch = d.get('chapter_index', '?')
            items = len(d['kis_guidance'])
            print(f'  Example: Chapter {ch} has {items} KIS items')
            break
else:
    print(f'\n[FAILED] No kis_guidance found in any doctrine')
    print(f'  First doctrine keys: {list(doctrines[0].keys())}')
    sys.exit(1)
