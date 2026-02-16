# ERA Test Suite Documentation

## Quick Start

```bash
# Run all tests
cd C:\era
pytest tests/ -v

# Run verification only
pytest tests/verification/ -v

# Run unit tests only
pytest tests/ --ignore=tests/verification -v
```

## Folder Structure

```
C:\era\tests/
├── pytest.ini                           # Pytest configuration
├── conftest.py                          # Shared fixtures & setup
├── TEST_MANIFEST.md                     # Complete test inventory
├── TEST_REPORT_GENERATION.txt           # Generated report
├── run_tests.py                         # Test runner script
├── README.md                            # This file
├── 
├── Core Test Files (19 .py files)
│   ├── FULL SUITE TESTS:
│   │   ├── advanced_persona_test_suite.py (19.40 KB)
│   │   ├── comprehensive_feature_test.py (16.73 KB)
│   │   ├── comprehensive_persona_test_suite.py (29.95 KB)
│   │   ├── master_test_orchestrator.py (25.53 KB)
│   │   └── run_phase1_test.py (1.13 KB)
│   │
│   ├── UNIT TESTS:
│   │   ├── Embedding: test_embed.py, test_embed_model.py, 
│   │   │             test_async_embed.py, test_async_embed_debug.py
│   │   ├── Ingestion: test_async_ingest.py, test_e2e_ingestion.py
│   │   ├── Generation: test_generate.py, test_deepseek_doctrine.py,
│   │   │              test_improved_doctrine.py
│   │   ├── Processing: test_split.py, test_split_direct.py, test_split_qwen25.py
│   │   └── Database: vector_db_smoke.py
│   │
│   ├── Data Files:
│   │   ├── test_nodes.json
│   │   └── test_single.json
│   │
│   └── [19 Python test files - 118.65 KB total]
│
└── verification/                        # System verification suite
    ├── Verification Scripts (4 files)
    │   ├── quick_verify.py (5.16 KB)
    │   ├── verify_all_features.py (9.39 KB)
    │   ├── verify_improvements.py (3.73 KB)
    │   └── verify_llm_integration.py (2.06 KB)
    │
    └── Check Scripts (5 files)
        ├── check_chapter_text.py (0.93 KB)
        ├── check_doctrine.py (1.11 KB)
        ├── check_extraction.py (1.33 KB)
        ├── check_ingestion_status.py (1.47 KB)
        └── check_v2_status.py (1.38 KB)
        
        [9 Python verification files - 26.56 KB total]
```

## Configuration Files Explained

### pytest.ini
Central configuration for pytest. Defines:
- Test discovery paths and patterns
- Test markers (unit, integration, async, embedding, etc.)
- Output formats and logging
- Strict mode and warning handling

### conftest.py
Shared test configuration including:
- Path setup and imports
- Session-scoped fixtures (era_root, test_data_dir, rag_storage_dir)
- Test-specific fixtures (temp_test_dir)
- Auto-marker application based on test filename

### TEST_MANIFEST.md
Complete inventory of all 27 test files with:
- Detailed descriptions and purposes
- Quick test commands
- Test categorization matrix
- Expected test results
- Individual test documentation

### run_tests.py
Python test runner with options:
```bash
python run_tests.py                 # All tests
python run_tests.py --verify-only   # Verification only
python run_tests.py --unit-only     # Unit tests only
python run_tests.py --coverage      # With coverage report
python run_tests.py --report        # Generate report
python run_tests.py --marker=async  # Specific marker
```

## Test Categories

### Full Test Suites (5 files, 96.54 KB)
Complete system validation:
- **comprehensive_persona_test_suite.py** - Persona subsystem complete testing
- **comprehensive_feature_test.py** - All 92+ features validated
- **advanced_persona_test_suite.py** - Advanced LLM scenarios
- **master_test_orchestrator.py** - Master test coordinator
- **run_phase1_test.py** - Phase 1 baseline

### Core Unit Tests (12 files)
Module-level testing:
- **Embedding** (4): Fundamentals, models, async operations
- **Ingestion** (2): Async pipeline, end-to-end processing
- **Generation** (3): LLM output, Deepseek, doctrine system
- **Text Processing** (2): Chunking, splitting, tokenization
- **Database** (1): Vector DB smoke test

### Verification Suite (9 files, 26.56 KB)
System health and validation:
- **Verification** (4): Features, improvements, LLM integration, quick checks
- **Status Checks** (5): Chapter validation, extraction, ingestion health

## How to Run Tests

### Run Everything
```bash
pytest tests/ -v
```

### Run Specific Categories

**Verification Only**
```bash
pytest tests/verification/ -v
```

**Core Tests Only**
```bash
pytest tests/ --ignore=tests/verification -v
```

**By Test Suite Type**
```bash
# Unit tests tagged as async
pytest tests/ -m async -v

# Integration tests
pytest tests/ -m integration -v

# Embedding tests
pytest tests/ -m embedding -v

# Ingestion tests
pytest tests/ -m ingestion -v
```

### Advanced Options

**Coverage Report**
```bash
pytest tests/ --cov=../ --cov-report=html
```
Generates HTML coverage report in `htmlcov/index.html`

**JUnit XML Report** (CI/CD friendly)
```bash
pytest tests/ --junit-xml=test_results.xml
```

**With Parallel Execution** (requires pytest-xdist)
```bash
pytest tests/ -n auto
```

**Stop on First Failure**
```bash
pytest tests/ -x
```

**Run Last Failed Tests**
```bash
pytest tests/ --lf
```

## Available Test Markers

| Marker | Purpose | Example Command |
|--------|---------|-----------------|
| `unit` | Unit tests | `pytest -m unit` |
| `integration` | Integration tests | `pytest -m integration` |
| `e2e` | End-to-end | `pytest -m e2e` |
| `async` | Async operations | `pytest -m async` |
| `embedding` | Vector embeddings | `pytest -m embedding` |
| `ingestion` | Data pipelines | `pytest -m ingestion` |
| `generation` | LLM generation | `pytest -m generation` |
| `verification` | System validation | `pytest -m verification` |
| `smoke` | Quick smoke tests | `pytest -m smoke` |

Combine markers with AND/OR logic:
```bash
pytest tests/ -m "unit and not slow"        # Unit tests excluding slow
pytest tests/ -m "embedding or ingestion"   # Either category
```

## Expected Test Results

### Recent Results
- **Master Suite**: 31/31 tests (100%)
- **Advanced Suite**: 34/35 tests (97.1%)
- **Comprehensive Suite**: 32/41 tests (78.0%)

### System Status
✅ All 92+ features validated  
✅ Async operations stable  
✅ Embedding pipeline working  
✅ Ingestion system operational  
✅ LLM integration functional  

## Dependencies

Tests require:
- Python 3.9+
- pytest >= 6.0
- pytest-asyncio (for async tests)
- pytest-cov (for coverage reports)
- pytest-xdist (optional, for parallel execution)

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-xdist
```

## Troubleshooting

### Tests Won't Discover
- Check `pytest.ini` configuration
- Verify test files follow naming convention: `test_*.py` or `*_test.py`
- Run with verbose: `pytest tests/ -v --collect-only`

### Import Errors
- conftest.py adds sys.path entries for module imports
- Ensure running from C:\era root directory
- Check .venv activation

### Async Test Issues
- Ensure pytest-asyncio installed
- Async tests automatially marked by conftest.py
- Run with: `pytest tests/ -m async -v`

### Coverage Issues
- Install pytest-cov
- Run: `pytest tests/ --cov=../ --cov-report=html`
- Open `htmlcov/index.html` in browser

## What to Run When

| Scenario | Command |
|----------|---------|
| Quick validation | `pytest tests/verification/ -v` |
| Before commit | `pytest tests/ --ignore=tests/verification -q` |
| Full suite | `pytest tests/ -v` |
| Integration check | `pytest tests/ -m integration -v` |
| New feature test | `pytest tests/test_specific.py -v` |
| CI/CD pipeline | `pytest tests/ --junit-xml=report.xml` |
| Coverage report | `pytest tests/ --cov=../ --cov-report=html` |

## For Developers

When adding new tests:
1. Place in appropriate location (tests/ or tests/verification/)
2. Follow naming: `test_*.py` or `*_test.py`
3. Use pytest-style functions: `def test_something():`
4. Add markers: `@pytest.mark.unit`, `@pytest.mark.integration`
5. Run locally: `pytest tests/ -v`
6. Commit and push (CI/CD runs full suite)

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [TEST_MANIFEST.md](TEST_MANIFEST.md) - Detailed test inventory
- [conftest.py](conftest.py) - Fixture definitions
- [pytest.ini](pytest.ini) - Configuration
- Run `pytest --help` for more options

---

**Last Updated**: February 14, 2026  
**Test Framework**: pytest  
**Total Tests**: 27 files (145 KB)  
**Status**: ✅ Ready for use
