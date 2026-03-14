# ERA Test Suite Manifest

## Overview
Complete test and verification suite for the ERA (Persona) system. All tests organized under `C:\era\tests\`.

## Refactor Coverage Additions (2026-03-11)
Added targeted tests for the refactored architecture:
- `test_failure_analysis.py` (failure classification + aggregation)
- `test_scenario_memory_index.py` (scenario memory index + retrieval formatting)
- `test_budget_metrics.py` (budget efficiency computations)
- `test_evaluation_engine_smoke.py` (EvaluationRunner smoke test)
- `test_section_smoke.py` (pipeline module catalog + stage verification)
- `test_uncertainty_calibration.py` (temperature + isotonic + calibration metrics)
- `test_rl_components.py` (GAE, buffers, PPO networks, trainer smoke)
- `test_decision_simulator_and_engine.py` (DecisionSimulator + OptionEvaluator)
- `test_scenario_memory_module.py` (ScenarioMemoryModule execution path)
- `test_expert_routing.py` (expert router + MoE helpers)
- `test_learning_core_features.py` (feature extraction + dataset utilities)
- `test_policy_value_models.py` (policy/value predictor round-trip)
- `test_controllers.py` (reasoning + mode controllers)
- `test_experiment_infra.py` (scheduler + experiment runner)
- `test_evaluation_engine_utils.py` (option matching + rubric + calibration)

## Running Tests

### Run all tests
```bash
cd C:\era
pytest tests/
```

### Run specific test category
```bash
pytest tests/ -m unit           # Unit tests only
pytest tests/ -m integration    # Integration tests only
pytest tests/ -m verification   # Verification suite
pytest tests/ -m embedding      # Embedding tests
pytest tests/ -m ingestion      # Ingestion tests
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run specific file
```bash
pytest tests/test_embed.py -v
```

---

## Test Suite Structure

### Core Test Files (19 files in C:\era\tests)

#### Full Suite Tests (5 files)
- **advanced_persona_test_suite.py** - Advanced LLM interaction scenarios
  - Dynamic test generation
  - Real-world conversation patterns
  - Stress testing
  
- **comprehensive_feature_test.py** - System-wide feature validation
  - All 92+ features tested
  - Cross-module integration
  - Expected: ~98.9% pass rate

- **comprehensive_persona_test_suite.py** - Complete persona subsystem tests
  - State management (state.py)
  - Cognitive brain (brain.py)
  - Knowledge engine (knowledge_engine.py)
  - Analysis module (analysis.py)
  
- **master_test_orchestrator.py** - Master test runner/coordinator
  - Orchestrates all test suites
  - Aggregates results
  - Generates reports
  
- **run_phase1_test.py** - Phase 1 baseline tests
  - Initial system validation
  - Core functionality checks

#### Unit & Module Tests (12 files)

**Embedding Tests (4 files)**
- `test_embed.py` - Basic embedding functionality
- `test_embed_model.py` - Embedding model operations
- `test_async_embed.py` - Asynchronous embedding
- `test_async_embed_debug.py` - Async embedding debugging

**Ingestion & Processing (3 files)**
- `test_minister_converter.py` - Minister data structure conversion

**Generation & LLM (3 files)**
- `test_generate.py` - LLM text generation
- `test_deepseek_doctrine.py` - DeepSeek model testing
- `test_improved_doctrine.py` - Doctrine system improvements

**Text Processing (2 files)**
- `test_split.py` - Document chunking
- `test_split_direct.py` - Direct text splitting
- `test_split_qwen25.py` - Qwen tokenization splitting

**Database & Storage (1 file)**
- `vector_db_smoke.py` - Vector database quick checks

---

### Verification & Checking Suite (9 files in C:\era\tests\verification)

#### Verification Scripts (4 files)
- **quick_verify.py** - Quick system health check
  - Confirms all features accessible
  - ~170 lines, lightweight
  
- **verify_all_features.py** - Complete feature inventory validation
  - Tests all 92+ implemented features
  - ~170 lines
  
- **verify_improvements.py** - Validation of recent improvements
  - ~115 lines
  
- **verify_llm_integration.py** - LLM service integration check
  - ~65 lines

#### System Check Scripts (5 files)
- **check_chapter_text.py** - Document chapter validation
- **check_doctrine.py** - Doctrine system checks
- **check_extraction.py** - Data extraction validation
- **check_ingestion_status.py** - Ingestion pipeline health
- **check_v2_status.py** - V2 ingestion system status

---

## Test Execution Matrix

### Test Categories & Markers

| Marker | Description | Files |
|--------|-------------|-------|
| `unit` | Unit tests | 12 test_*.py files |
| `integration` | Integration tests | 5 suite files |
| `e2e` | End-to-end tests | (legacy ingestion e2e removed) |
| `async` | Async operations | test_async_*.py (4 files) |
| `embedding` | Vector embeddings | test_embed*.py (4 files) |
| `ingestion` | RAG data ingestion | test_*ingest*.py (2 files) |
| `generation` | LLM generation | test_generate.py, test_*doctrine.py (3 files) |
| `verification` | System verification | verification/*.py (9 files) |
| `smoke` | Quick smoke tests | vector_db_smoke.py |

### Test Counts by Category

| Category | Count | Size |
|----------|-------|------|
| Full Test Suites | 5 | 96.54 KB |
| Unit Tests | 12 | 21.56 KB |
| Smoke Tests | 1 | 0.54 KB |
| Verification Scripts | 4 | 20.34 KB |
| Check Scripts | 5 | 6.22 KB |
| **TOTAL** | **27** | **145.20 KB** |

---

## Test Results & Expected Outcomes

### Recent Test Results
- **master_test_report.json**: 31/31 tests (100% pass rate)
- **advanced_test_report.json**: 34/35 tests (97.1% pass rate) 
- **test_report.json**: 32/41 tests (78.0% pass rate)
- **Overall**: 97+ tests across all suites

### Key Validations
✅ All 92+ features verified  
✅ Async operations stable  
✅ Embedding pipeline functional  
✅ Ingestion system operational  
✅ LLM integration working  

---

## Quick Test Commands

```bash
# Navigate to project root
cd C:\era

# Run all tests with summary
pytest tests/ -v --tb=short

# Run only verification tests
pytest tests/verification/ -v

# Run only core tests (exclude verification)
pytest tests/ --ignore=tests/verification -v

# Run async tests
pytest tests/ -m async -v

# Run embedding tests
pytest tests/ -m embedding -v

# Run with coverage report
pytest tests/ --cov=./ --cov-report=html

# Run specific suite
pytest tests/comprehensive_persona_test_suite.py -v

# Run with markers
pytest tests/ -m "unit and not slow" -v

# Generate JUnit XML report
pytest tests/ --junit-xml=test_results.xml
```

---

## Configuration Files

- **pytest.ini** - Main pytest configuration with test discovery and markers
- **conftest.py** - Shared fixtures and test setup
- **TEST_MANIFEST.md** - This file, test inventory and documentation

---

## Notes

- All test files follow pytest naming conventions (test_*.py, *_test.py)
- Tests use standard Python unittest.TestCase or pytest-style functions
- Fixtures defined in conftest.py are automatically available to all tests
- Async tests properly marked for separate execution if needed
- Verification suite can run independently for quick system validation

---

**Last Updated**: February 14, 2026  
**Test Framework**: pytest  
**Python Version**: 3.9+  
**Coverage**: 92+ system features validated
