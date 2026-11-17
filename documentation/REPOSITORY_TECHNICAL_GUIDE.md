# ERA Repository Technical Guide

## 1. Project Overview

ERA is a **self-improving AI decision advisor** built in Python 3.14/FastAPI. Given a user prompt, ERA normalizes the request, analyzes the problem domain, selects a reasoning mode, synthesizes knowledge from a local minister corpus, runs a minister-style council (5–18 specialists deliberating in their own voice via doctrine YAML personas + a local LLM), produces a final decision, and validates inter-stage contracts. Every turn is remembered (episodic memory), outcomes feed back into minister confidence weights (Bayesian), and the system gets sharper with use.

Two entry points:

- **`api.py`** — FastAPI HTTP server (primary interface, port 8765)
- **`persona/main.py`** — CLI interactive loop with synthetic-human simulation

Both reach the same underlying engine. The codebase also includes `run_refactored.py` / `system_main.py` as CLI wrappers around the decision pipeline.

Target users:

- Developers extending a staged orchestration pipeline
- Researchers experimenting with decision-routing and council-style reasoning
- Operators running a local advisory engine via HTTP API or CLI

Primary problem solved:

- Turn a free-form decision prompt into a structured, inspectable, multi-stage decision result with typed contracts, deterministic fallbacks, learning feedback loops, and optional observability

Domain:

- Decision support
- Orchestration architecture
- Local AI tooling
- Governance-style reasoning systems
- Self-improving advisor systems

## 2. Repository Structure

### Root

- [`api.py`](api.py): **primary entry point** — FastAPI HTTP server (port 8765) with `/chat`, `/feedback`, `/profile`, `/mode`, `/export/obsidian`
- [`run_refactored.py`](run_refactored.py): CLI entrypoint for the decision pipeline
- [`system_main.py`](system_main.py): compatibility shim that delegates to `run_refactored.py`
- [`persona/main.py`](persona/main.py): CLI interactive loop with synthetic-human simulation
- [`README.md`](README.md): high-level project readme
- [`requirements.txt`](requirements.txt): dependency list
- [`.env.example`](.env.example): sample environment configuration

### `config/`

- [`config/settings.py`](c:\era\config\settings.py): runtime settings model, environment loading, override normalization, invariant enforcement
- [`config/__init__.py`](c:\era\config\__init__.py): package exports and convenience resolver

Purpose:

- Centralize runtime configuration for the orchestrator and observability stack

### `core/`

- [`core/contracts/`](c:\era\core\contracts): typed contracts for inputs, outputs, events, errors, and module interfaces
- [`core/orchestrator/`](c:\era\core\orchestrator): generic staged pipeline runner
- [`core/observability/`](c:\era\core\observability): metrics, tracing, and structured logging

Purpose:

- Provide the reusable architecture primitives used by the decision pipeline

### `modules/`

Each subpackage is a pipeline stage or orchestration wrapper:

- `input_normalization`
- `runtime_config`
- `domain_analysis`
- `council_router`
- `knowledge_synthesis`
- `council_execution`
- `council_normalization`
- `prime_decision`
- `decision_packaging`
- `contract_validation`
- `decision_pipeline`

Purpose:

- Implement the business logic of the staged decision flow

### `modules/learning_core/`

- `feature_extractor.py`: shared embedding + TF-IDF feature generation for learning models
- `dataset_utils.py`: shared dataset loading and split helpers
- `knowledge_features.py`: lightweight knowledge-derived features from the principles corpus

Purpose:

- Shared learning utilities used by both policy and value networks

### `modules/value_model/`

- `model.py`: regression model selection (ridge/MLP/random forest)
- `train.py`: value model training pipeline
- `predictor.py`: runtime value scoring

Purpose:

- Value network: predicts decision quality given prompt + option + context

### `modules/policy_model/`

- `model.py`: policy model selection (logistic/random forest)
- `train.py`: policy model training pipeline
- `predictor.py`: runtime policy scoring

Purpose:

- Policy network: predicts option likelihoods to guide candidate selection

### `modules/decision_environment/`

- `environment.py`: simple reset/step interface for training loops
- `scenario_simulator.py`: wraps outcome model + reward computation
- `outcome_model.py`: heuristic outcome prediction for decisions
- `reward_function.py`: utility-based reward scoring

Purpose:

- Simulated environment for generating additional decision data beyond static benchmarks

### `modules/expert_router/`

- `expert_registry.py`: expert list + heuristic domain routing
- `router_model.py`: router model definition (logistic/random forest)
- `router_predictor.py`: runtime router inference (model or heuristic)
- `aggregator.py`: weighted aggregation for expert positions

Purpose:

- Learned (or heuristic) expert routing for council selection

Runtime controls:

- `expert_router_enabled`: boolean routing context flag
- `expert_router_top_k`: restrict to top-K experts
- `expert_router_path`: optional model directory for router inference

### `modules/council_learning/`

- `dataset_builder.py`: bootstraps training targets from scenario context
- `weight_model.py`: MLP/ridge weight model
- `train.py`: training pipeline for minister weights
- `predictor.py`: runtime weight inference

Runtime controls:

- `council_weight_model_enabled`: boolean flag to enable learned weighting
- `council_weight_model_path`: model directory for `CouncilWeightPredictor`
- `council_weight_top_k`: restrict to top-K ministers by learned weight

### `scripts/generate_simulated_data.py`

Generates synthetic outcome + reward rows by running each benchmark scenario through the decision environment.

Output (default):

- `data/simulated/decision_env.jsonl`

Each row includes:

- scenario_id
- prompt
- option
- context
- outcome
- reward

### `era_benchmark/`

- [`era_benchmark/benchmark_index.json`](c:\era\era_benchmark\benchmark_index.json): benchmark metadata (current version, counts)
- [`era_benchmark/schema.md`](c:\era\era_benchmark\schema.md): scenario schema and scoring rules
- `era_benchmark/scenarios/*`: 300 context-driven scenarios used for evaluation, training seeds, and regression checks

Purpose:

- Provide a frozen, deterministic evaluation dataset (ERA-Bench v1.1)
- Back value-model training and regression checks

Regeneration:

- [`scripts/generate_era_benchmark.py`](c:\era\scripts\generate_era_benchmark.py) rebuilds the dataset deterministically with a seed

### `evaluation/`

- [`evaluation/evaluate_benchmark.py`](c:\era\evaluation\evaluate_benchmark.py): wrapper CLI for the evaluation engine

Purpose:

- Quick evaluation runs over ERA-Bench without experiment harness overhead

### `experiments/`

- `experiments/run_benchmark.py`: experiment runner with metrics, plots, and bootstrap statistics
- `experiments/experiment_registry.py`: named experiment configs (baseline vs council modes, value model)

Purpose:

- Reproducible experiment execution with statistical reporting

### `scripts/`

- [`scripts/run_benchmark.py`](c:\era\scripts\run_benchmark.py): primary benchmark runner with split filtering
- [`scripts/generate_era_benchmark.py`](c:\era\scripts\generate_era_benchmark.py): ERA-Bench v1.1 generator

Purpose:

- CLI entrypoints and dataset tooling for evaluation and benchmarking

### `data/`

Contains local artifacts and reference data:

- `data/doctrine/locked/` — 18 minister YAML personas (speak/silent triggers, persona canon)
- `data/ministers/{domain}/` — `principles.json`, `rules.json`, `warnings.json`, `claims.json` per domain (the active knowledge source for KIS)
- `data/memory/episodes.jsonl` — all decision episodes (append-only JSONL)
- `data/memory/minister_confidence.json` — Bayesian per-minister×domain weights
- `data/user_profiles/` — persistent cross-session user identity
- `data/conversations/`, `data/sessions/`, `data/learning_insights/` — historical artifacts

Current runtime dependency:

- `data/ministers/` is the primary knowledge source — `persona/knowledge_engine.py` reads it directly
- `data/doctrine/locked/` is read by `persona/council/minister_voice.py` and `modules/council_execution/engine.py` for minister personas
- `data/memory/` and `data/user_profiles/` are written by the API layer

### `knowledge/`

- [`knowledge/principles.json`](c:\era\knowledge\principles.json): principle corpus used by knowledge synthesis
- `knowledge/embeddings.npy`: retained artifact, not part of the active runtime path

Purpose:

- Provide lightweight local knowledge for synthesis

### `logs/`

- Default sink for structured observability output when file logging is enabled

Default file:

- `logs/orchestration_events.jsonl`

### `tests/`

Contains both current refactored tests and older legacy-oriented tests/documentation.

Most relevant current tests cover:

- core contracts
- runtime settings
- input normalization
- domain analysis
- mode routing
- knowledge synthesis
- council execution
- council normalization
- prime decision
- decision packaging
- contract validation
- decision pipeline orchestration
- observability
- legacy import guardrails

### `documentation/`

Contains a mixture of:

- retained older docs
- forensic audit material
- cleanup notes
- this guide

Important:

- many existing docs in this folder still describe pre-refactor subsystems that no longer exist on `main`
- this file is intended to be the current runtime guide

## 3. Technology Stack

### Active runtime stack

The current refactored pipeline is predominantly standard-library Python:

- Python 3.12+
- `argparse`, `json`, `dataclasses`, `typing`, `pathlib`, `datetime`, `math`

Architecture style:

- plugin-like modules implementing a shared interface
- synchronous staged orchestration
- typed data contracts
- optional observability layer

### Declared dependencies

[`requirements.txt`](c:\era\requirements.txt) still declares a much larger stack, including:

- LLM tooling: `ollama`, `httpx`, `aiohttp`, `requests`
- data/ML: `numpy`, `pandas`, `scikit-learn`
- validation/config: `python-dotenv`, `pydantic`, `pydantic-settings`
- web/API: `fastapi`, `uvicorn`, `Flask`, `gunicorn`
- storage/vector: `sqlalchemy`, `psycopg2-binary`, `pgvector`, `faiss-cpu`
- testing/dev: `pytest`, `pytest-asyncio`, `pytest-cov`, `black`, `mypy`, `flake8`

Current reality:

- the active refactored CLI path does not require most of that stack
- many dependencies remain from the pre-refactor repository history

### Data and infrastructure

Current runtime:

- requires a local LLM via Ollama (for minister voice deliberation) — falls back to keyword scoring if unavailable
- uses ChromaDB for semantic knowledge retrieval (graceful fallback to keyword scan)
- uses SQLite (in-memory, per-thread) for council decision storage
- no external database required
- all state persisted to local JSON/JSONL files

## 4. System Architecture

### Architectural model

The system is built around a central synchronous orchestrator:

1. Build an `InputContract`
2. Create an `ExecutionContext`
3. Execute named stages in order
4. Store stage outputs in `context.state`
5. Record events and errors centrally
6. Post-process the orchestration result into a typed `DecisionPipelineResult`

### Core components

- [`PipelineOrchestrator`](c:\era\core\orchestrator\runtime.py): generic staged runner
- [`ExecutionContext`](c:\era\core\contracts\context.py): mutable run state
- [`ModulePlugin`](c:\era\core\contracts\module.py): interface for pipeline stages
- [`DecisionPipelineEngine`](c:\era\modules\decision_pipeline\engine.py): application-specific composition of stages
- [`DecisionPipelineTelemetryEngine`](c:\era\modules\decision_pipeline\telemetry.py): metrics/trace/log emission
- [`DecisionPipelineErrorEngine`](c:\era\modules\decision_pipeline\errors.py): structured issue normalization

### Stage order

The decision pipeline composes these core stages in this order:

1. `input_normalization`
2. `runtime_config`
3. `domain_analysis`
4. `mode_routing`
5. `knowledge_synthesis`
6. `council_execution`
7. `council_normalization`
8. `prime_decision`
9. `decision_packaging`
10. `contract_validation`

### Data flow

The main state flow is:

1. Raw CLI input becomes `InputContract`
2. Input normalization produces a `RequestContextContract` and normalized `routing_context`
3. Runtime config produces `RuntimeConfigContract` and resolved settings
4. Domain analysis produces `DomainAnalysisContract`
5. Mode routing produces `ModeResolutionContract`
6. Knowledge synthesis produces `KnowledgeContract`
7. Council execution produces raw `CouncilContract`-like data
8. Council normalization converts that into stable council outputs and `CouncilNormalizationContract`
9. Prime decision produces `DecisionContract`
10. Decision packaging produces `DecisionPackagingContract` and the final response payload
11. Contract validation checks consistency across the assembled state
12. Telemetry and error engines summarize the run after orchestration completes

### Extension model

The pipeline supports extension stages through:

- [`ExtensionStageSpec`](c:\era\modules\decision_pipeline\extensions.py)
- [`ExtensionStagePlanner`](c:\era\modules\decision_pipeline\extensions.py)

Extensions can be inserted:

- before a named stage
- after a named stage
- with `abort` or `degrade` error behavior

This is the repository's primary plugin mechanism in the current architecture.

## 5. Module Breakdown

### `input_normalization`

Files:

- [`modules/input_normalization/engine.py`](c:\era\modules\input_normalization\engine.py)
- [`modules/input_normalization/module.py`](c:\era\modules\input_normalization\module.py)

Purpose:

- Normalize requested mode
- Merge routing context from context config, input metadata, run metadata, and state
- Canonicalize aliases such as domains, confidence, risk/stakes, reversibility

Inputs:

- requested mode
- routing context from `ExecutionContext`

Outputs:

- normalized mode string
- normalized `routing_context`
- `RequestContextContract`

### `runtime_config`

Files:

- [`modules/runtime_config/engine.py`](c:\era\modules\runtime_config\engine.py)
- [`modules/runtime_config/module.py`](c:\era\modules\runtime_config\module.py)

Purpose:

- Load runtime settings from environment
- Apply runtime overrides from config/metadata/input metadata
- Enforce invariants, especially observability-related ones

Key env vars:

- `ERA_APP_NAME`
- `ERA_ENV`
- `ERA_ORCH_STRICT`
- `ERA_OBS_ENABLED`
- `ERA_OBS_EMIT_EVENTS`
- `ERA_OBS_EMIT_SUMMARY`
- `ERA_OBS_WRITE_FILE`
- `ERA_OBS_STDERR`
- `ERA_OBS_FILE`
- `ERA_DECISION_PIPELINE_ENABLED`

Outputs:

- runtime settings dictionary
- `RuntimeConfigContract`
- warnings about ignored or normalized overrides

### `domain_analysis`

Files:

- [`modules/domain_analysis/engine.py`](c:\era\modules\domain_analysis\engine.py)
- [`modules/domain_analysis/module.py`](c:\era\modules\domain_analysis\module.py)

Purpose:

- Infer problem domains, stakes, reversibility, and named entities

Implementation:

- Uses a native heuristic analyzer by default
- Supports an optional injected LLM adapter

Outputs:

- `DomainAnalysisContract`
- `domain_analysis_result`

### `council_router`

Files:

- [`modules/council_router/engine.py`](c:\era\modules\council_router\engine.py)
- [`modules/council_router/mode_orchestrator.py`](c:\era\modules\council_router\mode_orchestrator.py)

Purpose:

- Choose the reasoning mode
- Determine whether council execution is needed
- Select ministers
- Build mode-specific framing
- Compute execution flags

Supported modes in the orchestrator:

- `baseline`
- `quick`
- `meeting`
- `war`
- `darbar`

Mode semantics:

- `quick`: no council, direct response framing
- `meeting`: balanced multi-minister reasoning
- `war`: aggressive strategy framing with risk red-line constraints
- `darbar`: full council, doctrine-heavy deep reasoning
- `baseline`: ablation-style minimal plan

### `knowledge_synthesis`

Files:

- [`modules/knowledge_synthesis/engine.py`](c:\era\modules\knowledge_synthesis\engine.py)
- [`modules/knowledge_synthesis/module.py`](c:\era\modules\knowledge_synthesis\module.py)

Purpose:

- Select and rank principle-level knowledge relevant to the active domains and prompt

Implementation:

- Loads principles from `knowledge/principles.json`
- Falls back to `data/principles.json`
- Scores candidates by domain match, text overlap, and historical success rate

Outputs:

- `KnowledgeContract`
- `knowledge_result`

### `council_execution`

Files:

- [`modules/council_execution/engine.py`](c:\era\modules\council_execution\engine.py)
- [`modules/council_execution/module.py`](c:\era\modules\council_execution\module.py)

Purpose:

- Run the selected ministers and aggregate their positions

Implementation:

- Uses a native in-process `NativeCouncil`
- Ministers return stance, confidence, reasoning, and red-line flags
- Council execution respects mode behavior from `ModeOrchestrator`

Outputs:

- raw council result
- minister positions
- support/oppose/neutral counts
- consensus strength

### `council_normalization`

Files:

- [`modules/council_normalization/engine.py`](c:\era\modules\council_normalization\engine.py)
- [`modules/council_normalization/module.py`](c:\era\modules\council_normalization\module.py)

Purpose:

- Normalize heterogeneous council output into stable downstream structures

Outputs:

- normalized council payload
- normalized minister outputs
- council positions list
- `CouncilNormalizationContract`

### `prime_decision`

Files:

- [`modules/prime_decision/engine.py`](c:\era\modules\prime_decision\engine.py)
- [`modules/prime_decision/module.py`](c:\era\modules\prime_decision\module.py)

Purpose:

- Convert council outcomes into a single final decision

Implementation:

- Uses `NativePrimeDecider`
- Interprets support/oppose balance, red lines, confidence, and council recommendation

Possible outcomes:

- `accept`
- `accept_with_mitigation`
- `defer`
- `reject`
- `direct_response`

Outputs:

- final decision payload
- `DecisionContract`

### `decision_packaging`

Files:

- [`modules/decision_packaging/engine.py`](c:\era\modules\decision_packaging\engine.py)
- [`modules/decision_packaging/module.py`](c:\era\modules\decision_packaging\module.py)

Purpose:

- Produce the final user-facing packaged decision summary

Outputs:

- package with final outcome, reason, confidence, mode, council outcome, red lines, knowledge count, and follow-up flag
- `DecisionPackagingContract`

### `contract_validation`

Files:

- [`modules/contract_validation/engine.py`](c:\era\modules\contract_validation\engine.py)
- [`modules/contract_validation/module.py`](c:\era\modules\contract_validation\module.py)

Purpose:

- Validate that stage outputs are coherent with each other

Checks include:

- contract type presence
- council invocation alignment
- council normalization alignment
- decision contract and packaging alignment
- decision package shape and count consistency

Outputs:

- `ContractValidationContract`
- issue list

### `decision_pipeline`

Files:

- [`modules/decision_pipeline/engine.py`](c:\era\modules\decision_pipeline\engine.py)
- [`modules/decision_pipeline/module.py`](c:\era\modules\decision_pipeline\module.py)
- [`modules/decision_pipeline/telemetry.py`](c:\era\modules\decision_pipeline\telemetry.py)
- [`modules/decision_pipeline/errors.py`](c:\era\modules\decision_pipeline\errors.py)
- [`modules/decision_pipeline/extensions.py`](c:\era\modules\decision_pipeline\extensions.py)
- [`modules/decision_pipeline/__init__.py`](c:\era\modules\decision_pipeline\__init__.py)

Purpose:

- Compose all stage modules into the central application pipeline

Outputs:

- `DecisionPipelineResult`
- stage timings
- telemetry summary
- issue summary

## 6. Execution Flow

### Entry points

- [`run_refactored.py`](c:\era\run_refactored.py): canonical CLI
- [`system_main.py`](c:\era\system_main.py): compatibility wrapper

### Startup flow

1. CLI parses `--input`, `--mode`, and `--strict`
2. `DecisionPipelineEngine.create()` constructs all stage modules
3. If `--input` is provided, one run is executed
4. If no `--input` is provided, interactive loop starts

### Per-run flow

1. `DecisionPipelineEngine.run()` normalizes user input and metadata
2. It builds a `PipelineOrchestrator`
3. The orchestrator creates an `ExecutionContext`
4. Each stage runs in sequence and writes outputs into `context.state`
5. Events and errors are appended to the context
6. The orchestration result is converted into a `DecisionPipelineResult`
7. Telemetry and error summaries are computed after the pipeline run
8. CLI prints a JSON summary

### Example result shape

The CLI returns:

- overall status
- run id
- resolved mode
- whether council was invoked
- selected ministers
- final decision
- confidence
- rationale
- packaged final decision
- error and warning counts

## 7. Features

### Structured staged orchestration

- Named stages with explicit ordering
- Per-stage timings
- `abort` vs `degrade` error policies

### Typed contracts

- Every major boundary has a dataclass contract
- Contracts are normalized defensively
- Contract validation runs at the end of the pipeline

### Mode-based reasoning

- Multiple reasoning modes with different minister and execution behavior
- Optional uncertainty-driven escalation inside the mode orchestrator

### Native domain analysis

- Keyword-based domain inference
- Stakes and reversibility estimation
- Entity extraction
- Optional LLM-backed analysis if injected

### Native knowledge synthesis

- Principle selection from local JSON knowledge
- Scoring based on domain fit and text overlap

### Native minister council

- In-process council members
- Mode-aware minister selection
- Support, oppose, neutral stances
- Red-line signaling

### Prime decision authority

- Deterministic resolution from council outcomes
- Produces one final outcome with confidence and reason

### Observability

- event traces
- aggregate metrics
- optional JSONL logging to file and/or stderr

### Pipeline extension points

- Register extension stages before or after core stages
- Choose degrade or abort behavior

## 8. Installation Guide

### Prerequisites

- Windows, macOS, or Linux with Python 3.12+ recommended
- Git

### Minimal setup for current refactored runtime

The current runtime mostly uses the Python standard library. In practice, the simplest setup is:

```bash
cd c:\era
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Environment configuration

Create or update `.env` as needed. The most relevant current variables are:

```env
ERA_APP_NAME=era
ERA_ENV=development
ERA_ORCH_STRICT=false
ERA_OBS_ENABLED=true
ERA_OBS_EMIT_EVENTS=false
ERA_OBS_EMIT_SUMMARY=true
ERA_OBS_WRITE_FILE=false
ERA_OBS_STDERR=false
ERA_OBS_FILE=logs/orchestration_events.jsonl
ERA_DECISION_PIPELINE_ENABLED=true
```

### Database setup

None required for the current refactored runtime.

### LLM setup

Optional only.

The current CLI path works without an external LLM because domain analysis, knowledge synthesis, council execution, and prime decision all have native fallbacks.

## 9. Usage Guide

### CLI usage

HTTP API:

```bash
uvicorn api:app --reload --port 8765

# Chat
curl -X POST http://localhost:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Should we delay the release?"}'

# Feedback (closes learning loop)
curl -X POST http://localhost:8765/feedback \
  -H "Content-Type: application/json" \
  -d '{"session_id":"...", "turn":3, "helpful":true, "entries_used":[...]}'

# User profile
curl http://localhost:8765/profile/user42
```

CLI interactive:

```bash
python -m persona.main
```

CLI pipeline single run:

```bash
python run_refactored.py --input "Should we delay the release for compliance review?"
python run_refactored.py --input "We need a fast answer" --mode quick
python run_refactored.py --input "We need a high-stakes final ruling" --mode darbar
```

### Programmatic usage

```python
from modules.decision_pipeline import DecisionPipelineEngine

pipeline = DecisionPipelineEngine.create(strict=False)
result = pipeline.run(
    user_input="Should we postpone launch due to compliance risk?",
    requested_mode="meeting",
    source="script",
)

print(result.final_decision)
```

### Public interaction surface

| Interface | File | Port/Method |
|-----------|------|-------------|
| **HTTP API** | `api.py` | `uvicorn api:app --port 8765` |
| **CLI interactive** | `persona/main.py` | `python -m persona.main` |
| **CLI pipeline** | `run_refactored.py` | `python run_refactored.py --input "..."` |

API endpoints: `/chat`, `/feedback`, `/profile/{user_id}`, `/mode`, `/session/{id}`, `/sessions`, `/health`, `/export/obsidian`

### Observability usage

Enable summary file logging:

```env
ERA_OBS_ENABLED=true
ERA_OBS_EMIT_SUMMARY=true
ERA_OBS_WRITE_FILE=true
ERA_OBS_FILE=logs/orchestration_events.jsonl
```

Enable stderr event streaming:

```env
ERA_OBS_ENABLED=true
ERA_OBS_EMIT_EVENTS=true
ERA_OBS_STDERR=true
```

## 10. Testing

### Current test organization

86 test files, 461 tests collected. Key test files:

- `test_era_fixes.py` — 10 tests for BASE_PATH, PDF extraction, Chroma, thread-safety, doctrine YAML
- `test_era_upgrades.py` — 24 tests for feedback loop, user profiles, minister voice, auto-retrain, single-call classify, domain gaps, domain routing, Bayesian confidence, multi-round dialogue
- `test_decision_pipeline_engine.py` — 10-stage pipeline composition
- `test_council_execution.py` — NativeCouncil, keyword + LLM deliberation
- `test_knowledge_synthesis.py` — KIS scoring, principle selection
- `test_domain_analysis.py` — domain inference, stakes, reversibility
- `test_contracts_*.py` — typed I/O, context, events
- `test_observability_*.py` — logging, metrics, tracing
- `test_uncertainty_calibration.py` — temperature, isotonic, risk model

### Recommended commands

Smoke test (HTTP API):

```bash
uvicorn api:app --reload --port 8765
curl http://localhost:8765/health
```

Smoke test (CLI):

```bash
python run_refactored.py --input "Need a release decision"
```

ERA fix + upgrade tests:

```bash
pytest tests/test_era_fixes.py tests/test_era_upgrades.py -v
```

Pipeline stage tests:

```bash
pytest tests/test_decision_pipeline_engine.py tests/test_council_execution.py tests/test_knowledge_synthesis.py tests/test_domain_analysis.py -v
```

Full test suite:

```bash
pytest tests/ -v
```

### Coverage observations

The active runtime is well covered at the unit and contract level. However:

- `tests/README.md` is stale and still describes removed subsystems
- several tests in `tests/` are historical and no longer represent the active runtime path

## 11. Limitations and Risks

### Stale documentation

Several older documents in `documentation/` and `documentation/legacy_notes/` still describe pre-refactor subsystems. The following are the current source-of-truth documents:

- `PROJECT_OVERVIEW.md` — architecture, memory systems, API endpoints
- `documentation/REPOSITORY_TECHNICAL_GUIDE.md` (this file) — repo structure, modules, contribution guide
- `README.md` — quick start, entry points
- `ERA_FIX_PLAN.md` / `ERA_UPGRADE_PLAN.md` — completed fix and upgrade task tracking

### Declared dependencies exceed active runtime needs

`requirements.txt` still contains legacy-era dependencies for web, database, vector, and ML stacks that are not part of the active pipeline path.

Risk:

- installation cost is higher than necessary
- new contributors may infer capabilities that no longer exist

### Baseline mode mismatch

The mode orchestrator supports `baseline`, but input normalization currently only treats `quick`, `meeting`, `war`, and `darbar` as valid request modes.

Implication:

- public CLI requests for `--mode baseline` may normalize to `meeting` instead of reaching baseline behavior

### Non-fatal telemetry warning in normal smoke runs

A standard single-run CLI smoke test currently emits:

- `pipeline_warning:telemetry_metadata_invalid_type`

This does not break execution, but it indicates a metadata-shape mismatch in telemetry collection.

### Retained inactive data

`data/` still contains many retained assets that are not wired into the active runtime path.

Risk:

- the repo still looks larger and more feature-complete than the current execution path actually is

### Runtime surface

The system has three interfaces:

- **HTTP API** (`api.py`) — FastAPI with full REST endpoints, session management, feedback loop, user profiles, Obsidian export
- **CLI interactive** (`persona/main.py`) — REPL with synthetic-human simulation
- **CLI pipeline** (`run_refactored.py`) — single-shot decision pipeline

No authenticated service layer or web UI exists yet.

## 12. Contribution Guide

### Where to work

For active runtime work, focus on:

- [`config/`](c:\era\config)
- [`core/`](c:\era\core)
- [`modules/`](c:\era\modules)
- [`tests/`](c:\era\tests)

Avoid using older docs as the source of truth unless they are explicitly about the current refactored architecture.

### How to add a new feature

1. Decide whether it is a new stage, an extension stage, or a change inside an existing stage.
2. If it is a new reusable stage, implement a `ModulePlugin`-compatible module.
3. Add or update contracts in [`core/contracts/io.py`](c:\era\core\contracts\io.py) if new typed boundaries are needed.
4. Register the stage in [`modules/decision_pipeline/engine.py`](c:\era\modules\decision_pipeline\engine.py) or via extension registration.
5. Add focused tests in `tests/`.

### Coding conventions implied by the current codebase

- dataclass-based contracts
- strong normalization of untrusted input
- mapping/iterable coercion guards
- explicit warning generation instead of silent failure
- deterministic fallbacks preferred over hidden hard dependencies

### Recommended contribution workflow

1. Run a smoke command before changing behavior.
2. Modify the smallest relevant module.
3. Add or update focused unit tests.
4. Run the relevant test subset.
5. If the change affects architecture or usage, update this guide and the root readme.

### Best place to extend behavior safely

- Use extension stages via [`modules/decision_pipeline/extensions.py`](c:\era\modules\decision_pipeline\extensions.py) when possible.
- This avoids destabilizing the core stage order.

## 13. Practical Summary

The current repository is best understood as a refactored decision-pipeline framework with a local CLI front end. The active architecture is coherent and testable, but the repository still contains stale documentation and oversized dependency declarations from the earlier, broader system. Developers should treat `core/`, `modules/`, `config/`, and the refactored tests as the current source of truth.
