# Phase 0 — Stabilize the Current System

Status: in progress (cleanup + architecture freeze)

Scope: refactored ERA pipeline (CLI-first) plus active learning, evaluation, and simulation layers.

This document delivers the Phase 0 artifacts:
1. Core pipeline diagram
2. Dependency graph (high-level)
3. Clean module tree (active vs legacy vs data)
4. Dead-code removal actions (performed) and remaining candidates
5. Connectivity verification summary

---

## 1) Core Pipeline Diagram (Refactored Runtime)

```
User Input
  ↓
Input Normalization
  ↓
Runtime Config
  ↓
Domain Analysis
  ↓
Mode Routing (adaptive compute)
  ↓
Knowledge Synthesis
  ↓
Council Execution
  ↓
Council Normalization
  ↓
Prime Decision
  ↓
Decision Packaging
  ↓
Contract Validation + Telemetry
  ↓
Structured Output (JSON)
```

Entry points:
- `run_refactored.py`
- `system_main.py` (shim)

Primary pipeline engine:
- `modules/decision_pipeline/engine.py`

---

## 2) Dependency Graph (High-Level)

```mermaid
flowchart TD
  CLI[run_refactored.py] --> PIPE[DecisionPipelineEngine]
  PIPE --> ORCH[PipelineOrchestrator]
  PIPE --> INORM[input_normalization]
  PIPE --> RCONF[runtime_config]
  PIPE --> DAN[domain_analysis]
  PIPE --> ROUTE[council_router]
  PIPE --> KIS[knowledge_synthesis]
  PIPE --> CEXEC[council_execution]
  PIPE --> CNORM[council_normalization]
  PIPE --> PRIME[prime_decision]
  PIPE --> PACK[decision_packaging]
  PIPE --> CVAL[contract_validation]
  PIPE --> OBS[observability]

  ROUTE --> MODECTL[Mode/Reasoning controller]
  CEXEC --> EXPRT[Expert Router (optional)]
  CEXEC --> CLRN[Council Learning (optional)]

  EVAL[Evaluation Engine] --> PIPE
  EVAL --> POL[Policy Model]
  EVAL --> VAL[Value Model]
  EVAL --> CAL[Calibration]
  EVAL --> UNC[Uncertainty]

  TRAIN[Training Loop] --> ENV[Decision Environment]
  TRAIN --> POL
  TRAIN --> VAL
  TRAIN --> EVAL

  ENV --> SIM[Scenario/Outcome Simulator]
  ENV --> RW[Reward Model]
```

---

## 3) Clean Module Tree (Active vs Legacy)

### Active runtime core
- `config/`
- `core/`
- `modules/` (pipeline stages + learning + evaluation + routing + calibration)
- `run_refactored.py`
- `system_main.py`

### Active learning + evaluation
- `decision_env/` (one-step, multi-step, long-horizon)
- `evaluation/` (quick bench CLI)
- `experiments/` (multi-run stats + plots + failure analysis)
- `training_loop/`
- `modules/rl/`

### Active data + assets
- `era_benchmark/` (dataset + splits)
- `knowledge/` (principles)
- `data/` (models, artifacts, runs)

### Legacy/auxiliary (not in core pipeline)
- `persona/` (legacy reasoning subsystem)
- `sovereign/` (legacy runtime components)
- `multi_agent_sim/`
- `hse/`
- `ingestion/` (still used for KIS/book ingestion but not in decision pipeline)

---

## 4) Dead Code Removal (Phase 0)

### Actions performed
- Removed legacy async ingestion stack and its tests (see below).

### Pending cleanup (blocked by policy)
Transient test artifacts remain because deletion commands were blocked by policy:
- `.pytest_cache/`
- `.pytest_tmp/`
- `_pytest_tmp/`
- `_pytest_tmp_run/`
- `__pycache__/`

These are non-source artifacts and do not affect the runtime. Remove manually if desired.

### Legacy async ingestion stack (removed)

The following legacy files and their associated tests have been removed:

- `adaptive_controller.py`
- `distributed_queue.py`
- `ingest_workers.py`
- `benchmark_harness.py`
- `async_ingestion_orchestrator.py`
- `async_ingest_orchestrator.py`

Removed tests:

- `tests/test_async_ingestion.py`
- `tests/test_async_ingest.py`
- `tests/async_ingest_orchestrator.py`
- `tests/async_ingest_config.py`
- `tests/test_e2e_ingestion.py`

---

## 5) Connectivity Verification Summary

### Core pipeline connectivity
Verified connections:
- CLI entrypoints → `DecisionPipelineEngine`
- `DecisionPipelineEngine` → `PipelineOrchestrator`
- `PipelineOrchestrator` → all stage modules
- `contract_validation` consumes outputs of prior stages
- `observability` receives stage events + run summaries

### Learning + evaluation connectivity
Verified connections:
- `EvaluationRunner` uses `DecisionPipelineEngine`, `PolicyModelPredictor`, `ValueModelPredictor`, `RiskModel`
- `OptionEvaluator` uses the same stack for hybrid scoring
- `Experiment runner` writes metrics + traces + plots and integrates failure analysis

### Simulation connectivity
Verified connections:
- `run_refactored.py` → `decision_env` (one-step, multi-step, long-horizon)
- `training_loop/` uses `decision_env` + policy/value training

### Non-core modules
Not connected to the refactored runtime (safe to ignore or remove later):
- `persona/`, `sovereign/`, `multi_agent_sim/`, `hse/`
- legacy ingestion async stack (see list above)

---

## 6) Architecture Freeze (Phase 0 Exit Criteria)

The current architecture is frozen at:
- Core pipeline in `modules/decision_pipeline`
- Entry points: `run_refactored.py`, `system_main.py`
- Evaluation: `modules/evaluation_engine` + `experiments/`
- Learning: `modules/policy_model`, `modules/value_model`, `modules/council_learning`, `modules/expert_router`
- Simulation: `decision_env/` (including long-horizon mode)

Any modifications beyond Phase 0 should:
- preserve the stage order
- update contracts when changing payload structure
- update this doc and the technical guide

---

## Phase 2 Note (Council Policy Conversion)

Phase 2 introduces learned minister policies. This is implemented under:

- `modules/minister_policies/`
- integrated into `modules/council_execution/engine.py`

Runtime toggle:
- `use_learned_ministers: true`
- `minister_policy_path: "data/minister_policies"`
