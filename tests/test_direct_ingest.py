import sys, json, shutil
from pathlib import Path

# Clean
storage = Path(r'C:\era\ingestion\v2\rag_storage\test_direct_ingest')
if storage.exists():
    shutil.rmtree(storage)

# Run ingestion on the test book
sys.path.insert(0, r'C:\era')
from ingestion.v2.src.ingest_pipeline import run_full_ingest_with_resume

book_path = r'C:\era\data\books\16-05-2021-070111The-Richest-Man-in-Babylon.pdf'
print(f'Starting ingestion of {Path(book_path).name}...')
run_full_ingest_with_resume(book_path, resume=False)
print(f'\nIngestion complete')

# Check doctrines
doc_path = storage / '02_doctrine.json'
if doc_path.exists():
    with open(doc_path) as f:
        doctrines = json.load(f)
    with_kis = sum(1 for d in doctrines if 'kis_guidance' in d)
    print(f'FINAL: {with_kis}/{len(doctrines)} doctrines have kis_guidance')
else:
    print(f'ERROR: Doctrine file not found at {doc_path}')
