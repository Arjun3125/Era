# ERA Test Suite

## Quick Start

```bash
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\python -m pytest tests/ -v
```

## Test Counts

- **86 test files** (test_*.py)
- **461 tests collected** (as of Sep 2026)
- **Python 3.14**, pytest 9.x

## Folder Structure

```
tests/
├── conftest.py                          # Shared fixtures & auto-markers
├── pytest.ini                           # Pytest configuration
├── TEST_MANIFEST.md                     # Detailed test inventory
├── README.md                            # This file
│
├── ERA Fix & Upgrade Tests (core)
│   ├── test_era_fixes.py                # 10 tests — BASE_PATH, PDF, Chroma, thread-safety, doctrine YAML
│   └── test_era_upgrades.py             # 24 tests — feedback loop, user profiles, minister voice,
│                                        #   auto-retrain, single-call classify, domain gaps,
│                                        #   domain routing, Bayesian confidence, multi-round dialogue
│
├── Pipeline Stage Tests
│   ├── test_input_normalization.py      # Input normalization engine
│   ├── test_domain_analysis.py          # Domain inference, stakes, reversibility
│   ├── test_knowledge_synthesis.py      # KIS scoring, principle selection
│   ├── test_council_execution.py        # NativeCouncil, keyword + LLM deliberation
│   ├── test_council_normalization.py    # Council output normalization
│   ├── test_prime_decision.py           # Final decision resolution
│   ├── test_decision_packaging.py       # User-facing decision summary
│   ├── test_decision_pipeline_engine.py # 10-stage pipeline composition
│   ├── test_decision_pipeline_*.py      # Telemetry, errors, extensions, module
│   ├── test_mode_routing.py             # Mode selection and minister routing
│   ├── test_runtime_config_engine.py    # Environment settings and invariants
│   └── test_contract_validation.py      # Cross-stage contract checks
│
├── Contract & Architecture Tests
│   ├── test_contracts_io.py             # Typed I/O contracts
│   ├── test_contracts_context.py        # ExecutionContext contracts
│   ├── test_contracts_events.py         # Event contracts
│   ├── test_config_settings.py          # Settings model
│   ├── test_core_orchestrator_runtime.py # Pipeline orchestrator
│   └── test_no_legacy_pipeline_imports.py # Import guardrail
│
├── Observability Tests
│   ├── test_observability_logger.py
│   ├── test_observability_metrics.py
│   └── test_observability_tracing.py
│
├── ML & Learning Tests
│   ├── test_step4_training_data.py      # ML outcome recording → training → model
│   ├── test_uncertainty_calibration.py  # Temperature, isotonic, risk model
│   ├── test_policy_value_models.py      # Policy and value network components
│   ├── test_rl_components.py            # PPO training components
│   ├── test_decision_env.py             # Decision simulation environment
│   └── test_scenario_memory_*.py        # FAISS scenario retrieval
│
├── EARS Mobile Pipeline Tests
│   ├── test_ears_pipeline.py
│   ├── test_ears_phase3.py
│   └── test_ears_upgrades.py
│
├── Integration & Smoke Tests
│   ├── test_llm_kis_integration.py      # LLM ↔ KIS integration
│   ├── test_kis_integration.py          # KIS end-to-end
│   ├── test_expert_routing.py           # Expert router
│   └── test_evaluation_engine_smoke.py  # Evaluation engine
│
├── Legacy / Utility Tests (retained)
│   ├── advanced_persona_test_suite.py
│   ├── comprehensive_feature_test.py
│   ├── comprehensive_persona_test_suite.py
│   ├── master_test_orchestrator.py
│   ├── run_phase1_test.py
│   ├── run_tests.py
│   └── verify_*.py
│
└── verification/                        # System verification scripts
    ├── quick_verify.py
    ├── verify_all_features.py
    └── ...
```

## How to Run

### Run All Tests

```bash
.venv\Scripts\python -m pytest tests/ -v
```

### Run ERA Fix & Upgrade Tests (most relevant)

```bash
.venv\Scripts\python -m pytest tests/test_era_fixes.py tests/test_era_upgrades.py -v
```

### Run Pipeline Stage Tests

```bash
.venv\Scripts\python -m pytest tests/test_decision_pipeline_engine.py tests/test_council_execution.py tests/test_knowledge_synthesis.py tests/test_domain_analysis.py -v
```

### Run Contract & Architecture Tests

```bash
.venv\Scripts\python -m pytest tests/test_contracts_*.py tests/test_config_*.py tests/test_core_*.py -v
```

### Run Specific Test

```bash
.venv\Scripts\python -m pytest tests/test_era_upgrades.py::test_reinforce_entry_increments_count -v
```

### Stop on First Failure

```bash
.venv\Scripts\python -m pytest tests/ -x
```

### Coverage Report

```bash
.venv\Scripts\python -m pytest tests/ --cov=persona --cov=modules --cov=api --cov-report=html
```

## Test Categories

| Category | Files | What it covers |
|----------|-------|----------------|
| ERA Fixes | `test_era_fixes.py` | BASE_PATH, PDF extraction, Chroma, thread-safety, doctrine YAML |
| ERA Upgrades | `test_era_upgrades.py` | Feedback loop, user profiles, minister voice, auto-retrain, multi-round |
| Pipeline | `test_decision_pipeline_*.py` | 10-stage pipeline, telemetry, errors, extensions |
| Council | `test_council_*.py` | NativeCouncil, deliberation, normalization |
| Knowledge | `test_knowledge_synthesis.py` | KIS scoring, principle selection, Chroma retrieval |
| Contracts | `test_contracts_*.py` | Typed I/O, context, events |
| Observability | `test_observability_*.py` | Logging, metrics, tracing |
| ML | `test_step4_*.py`, `test_uncertainty_*.py` | Training data, calibration, RL |

## Environment

```bash
# Virtual environment
cd C:\Users\naren\Work\Projects\School\era
.venv\Scripts\activate

# Key env vars for tests
ERA_MINISTER_PATH=data/ministers    # override minister JSON path
ERA_PROFILE_PATH=data/user_profiles # override profile storage
```

## Dependencies

- Python 3.14+
- pytest >= 9.0
- fastapi (for API tests)
- pdfplumber (for PDF extraction tests)
- chromadb (for semantic retrieval tests, graceful fallback)
- pyYAML (for doctrine loading tests)

---

**Last Updated**: September 2026
