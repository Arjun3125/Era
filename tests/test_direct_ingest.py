import sys, json, shutil, os
try:
    import pytest

    if os.getenv("ERA_RUN_INGESTION_TESTS", "").lower() not in ("1", "true", "yes"):
        pytest.skip(
            "ingestion test; set ERA_RUN_INGESTION_TESTS=1 to run",
            allow_module_level=True,
        )
except Exception:
    pass
from pathlib import Path

def test_direct_ingest():
    # Run ingestion on the test book
    sys.path.insert(0, r'C:\era')
    from ingestion.v2.src.ingest_pipeline import run_full_ingest_with_resume

    book_path = r'C:\era\data\books\16-05-2021-070111The-Richest-Man-in-Babylon.pdf'
    book_id = Path(book_path).stem
    base_storage = Path(r'C:\era\ingestion\v2\rag_storage')
    storage = base_storage / book_id

    # Clean
    if storage.exists():
        shutil.rmtree(storage)

    print(f'Starting ingestion of {Path(book_path).name}...')
    run_full_ingest_with_resume(book_path, resume=False)
    print(f'\nIngestion complete')

    # Check doctrines
    doc_path = storage / '02_doctrine.json'
    if not doc_path.exists():
        # Fallback to most recent doctrine file if storage name differs
        candidates = sorted(
            base_storage.glob("*\\02_doctrine.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            doc_path = candidates[0]

    if not doc_path.exists():
        raise AssertionError(f"Doctrine file not found at {doc_path}")

    with open(doc_path) as f:
        doctrines = json.load(f)
    with_kis = sum(1 for d in doctrines if 'kis_guidance' in d)
    print(f'FINAL: {with_kis}/{len(doctrines)} doctrines have kis_guidance')
