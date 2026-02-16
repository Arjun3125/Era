"""
Verification script: confirms all async pipeline components are in place.
Run this to validate installation before integrating into your system.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, r'c:\era\ingestion\v2\src')

print("=" * 70)
print("ASYNC INGESTION PIPELINE - INSTALLATION VERIFICATION")
print("=" * 70 + "\n")

files_required = [
    "async_ingest_config.py",
    "rate_controller.py",
    "ingest_metrics.py",
    "async_workers.py",
    "async_ingest_orchestrator.py",
    "test_async_ingest.py",
    "demo_async_pipeline.py",
    "integration_examples.py",
    "README_ASYNC_PIPELINE.md",
    "ASYNC_PIPELINE_GUIDE.py",
    "IMPLEMENTATION_SUMMARY.txt",
    "DELIVERABLES.md",
]

src_dir = Path(r'c:\era\ingestion\v2\src')

print("1. CHECKING FILES")
print("-" * 70)
all_present = True
for fname in files_required:
    fpath = src_dir / fname
    if fpath.exists():
        size_kb = fpath.stat().st_size / 1024
        print("  ✓ %-50s %8.1f KB" % (fname, size_kb))
    else:
        print("  ✗ %-50s MISSING" % fname)
        all_present = False

if not all_present:
    print("\nERROR: Some files are missing!")
    sys.exit(1)

print("\n2. CHECKING IMPORTS")
print("-" * 70)
modules = [
    "async_ingest_config",
    "rate_controller",
    "ingest_metrics",
    "async_workers",
    "async_ingest_orchestrator",
]

all_imported = True
for mod in modules:
    try:
        __import__(mod)
        print("  ✓ %-50s OK" % mod)
    except Exception as e:
        print("  ✗ %-50s %s" % (mod, e))
        all_imported = False

if not all_imported:
    print("\nERROR: Import failures!")
    sys.exit(1)

print("\n3. CHECKING CORE CLASSES")
print("-" * 70)

try:
    from async_ingest_config import Chunk
    print("  ✓ Chunk" + " " * 42 + "dataclass OK")
except Exception as e:
    print(f"  ✗ Chunk dataclass import failed: {e}")
    sys.exit(1)

try:
    from rate_controller import AdaptiveRateController
    print("  ✓ AdaptiveRateController" + " " * 27 + "class OK")
except Exception as e:
    print(f"  ✗ AdaptiveRateController import failed: {e}")
    sys.exit(1)

try:
    from ingest_metrics import IngestMetrics
    print("  ✓ IngestMetrics" + " " * 37 + "class OK")
except Exception as e:
    print(f"  ✗ IngestMetrics import failed: {e}")
    sys.exit(1)

try:
    from async_ingest_orchestrator import AsyncIngestionPipeline, main_ingest
    print("  ✓ AsyncIngestionPipeline" + " " * 32 + "class OK")
    print("  ✓ main_ingest" + " " * 42 + "function OK")
except Exception as e:
    print(f"  ✗ Orchestrator import failed: {e}")
    sys.exit(1)

print("\n4. TESTING BASIC FUNCTIONALITY")
print("-" * 70)

# Test Chunk
try:
    chunk = Chunk(
        text="test",
        domain="base",
        category="principles",
        embedding=[0.1] * 1536,
    )
    assert chunk.domain == "base"
    assert len(chunk.embedding) == 1536
    db_tuple = chunk.to_db_tuple()
    assert len(db_tuple) == 8
    print("  ✓ Chunk functionality" + " " * 34 + "OK (UUID: %s...)" % chunk.id[:8])
except Exception as e:
    print(f"  ✗ Chunk test failed: {e}")
    sys.exit(1)

# Test Metrics
try:
    metrics = IngestMetrics()
    metrics.record_embed(0.5)
    metrics.record_processed(100)
    report = metrics.report()
    assert report['processed_chunks'] == 100
    print("  ✓ IngestMetrics functionality" + " " * 27 + "OK")
except Exception as e:
    print(f"  ✗ Metrics test failed: {e}")
    sys.exit(1)

# Test RateController
try:
    ctrl = AdaptiveRateController(initial_concurrency=5, max_concurrency=20, min_concurrency=2)
    ctrl.record_success(0.4)
    ctrl.adjust()
    assert ctrl.concurrency >= 5  # May have increased
    print("  ✓ AdaptiveRateController functionality" + " " * 17 + "OK")
except Exception as e:
    print(f"  ✗ RateController test failed: {e}")
    sys.exit(1)

print("\n5. CHECKING DEPENDENCIES")
print("-" * 70)

deps = ['aiohttp', 'asyncpg']
for dep in deps:
    try:
        __import__(dep)
        print("  ✓ %-50s installed" % dep)
    except ImportError:
        print("  ✗ %-50s NOT installed" % dep)
        print("\n     Install with: pip install %s" % dep)

print("\n6. CONFIGURATION CHECK")
print("-" * 70)

try:
    from async_ingest_config import (
        MAX_EMBED_CONCURRENCY,
        EMBED_BATCH_SIZE,
        DB_BATCH_SIZE,
        MINISTER_BATCH_SIZE,
        QUEUE_MAXSIZE,
    )
    print("  ✓ MAX_EMBED_CONCURRENCY" + " " * 35 + str(MAX_EMBED_CONCURRENCY))
    print("  ✓ EMBED_BATCH_SIZE" + " " * 39 + str(EMBED_BATCH_SIZE))
    print("  ✓ DB_BATCH_SIZE" + " " * 43 + str(DB_BATCH_SIZE))
    print("  ✓ MINISTER_BATCH_SIZE" + " " * 37 + str(MINISTER_BATCH_SIZE))
    print("  ✓ QUEUE_MAXSIZE" + " " * 44 + str(QUEUE_MAXSIZE))
except Exception as e:
    print(f"  ✗ Configuration check failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE - ALL SYSTEMS GO")
print("=" * 70)
print("\nNext steps:")
print("  1. Adapt your parser to return List[Chunk]")
print("  2. Call: await main_ingest(book_paths, my_parse, num_embed_workers=20)")
print("  3. Or run: python demo_async_pipeline.py")
print("  4. See: README_ASYNC_PIPELINE.md for full documentation")
print("\n" + "=" * 70 + "\n")

sys.exit(0)
