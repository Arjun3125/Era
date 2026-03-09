# B01 Feature and Responsibility Map

## Runtime Decision Engine
- `persona/main.py`
  - Interactive runtime loop.
  - Session continuity and contextual prompt assembly.
  - Delegates to mode orchestrator and dynamic council.
  - Optional learning/event recording integration.
- `system_main.py`
  - Unified ERA orchestrator path with explicit setup and execution telemetry.
- `persona/ollama_runtime.py`
  - LLM transport and deterministic generation options.
  - Fail-fast toggle controlled by `EVAL_FAIL_FAST_ERRORS`.
  - Startup daemon readiness check guarded by `SKIP_OLLAMA_CHECK`.
- `persona/modes/mode_orchestrator.py`
  - Mode policies (`baseline`, `quick`, `war`, `meeting`, `darbar`).
  - Composite uncertainty calculation and policy action selection.
- `persona/council.py`, `persona/council/dynamic_council.py`, `persona/ministers.py`
  - Minister generation and aggregation mechanics.
  - Dynamic minister subset selection based on mode and context.

## Scoring and Benchmarking
- `run_benchmark.py`
  - Canonical benchmark runner, baseline vs council comparison.
  - Emits per-scenario scoring artifacts.
- `evaluation/evaluation_runner.py`
  - Dataset loading, execution, scoring collection, metrics bookkeeping.
- `evaluation/scoring/outcome_scorer.py`
  - Rubric path matching + principle matching (strict/semantic).
- `evaluation/scoring/regret_scorer.py`
  - Regret severity mapping from rubric outcomes.
- `evaluation/scoring/rubric_engine.py`
  - Scenario/rubric loading and integrity verification.

## Phase2 and Robustness Control
- `evaluation/run_phase2_robustness.py`
  - Full phase2 matrix runner (core/adversarial/OOD + ablations).
  - Timeout/deadline controls.
  - Split-manifest integration.
  - Uncertainty runtime percentile two-pass probing.
  - Milestone4 extensions (self-play, shift, governance tests).
- `evaluation/run_phase2_with_gates.py`
  - Wrapper with preflight Ollama availability checks and gate evaluation hooks.

## Uncertainty and Calibration
- `evaluation/uncertainty_analysis.py`
  - Reliability, calibration, uncertainty feature synthesis.
  - Supports learned uncertainty fitting/evaluation flows.
- `evaluation/learned_uncertainty.py`
  - Frozen uncertainty model loading and inference.
- `evaluation/reliability_analysis.py`
  - Reliability curves and ECE/Brier style reporting.

## Gating and Routing
- `evaluation/gating_support.py`
  - Feature extraction for minister-level and scenario-level routing signals.
- `evaluation/gating_model.py`
  - MLP-based minister weighting model and training routines.
- `evaluation/train_phase2_gating.py`, `evaluation/build_phase2_gating_dataset.py`
  - Dataset assembly and offline training orchestration.

## Knowledge Integration (KIS2)
- `evaluation/kis2_retrieval.py`
  - Embedding retrieval + optional reranker for principle injection.
- `evaluation/build_kis2_index.py`, `evaluation/train_kis2_reranker.py`
  - Index creation and reranker training path.

## Milestone4 Stress Modules
- `evaluation/adversarial_user_simulator.py`
  - Adversarial scenario perturbation generation for self-play.
- `evaluation/distribution_shift.py`
  - Structured shift transformations (time pressure, sparse info, value conflict).
- `evaluation/red_team_governance.py`
  - Governance and integrity red-team probes.
- `evaluation/run_phase4_stress.py`
  - Unified stress invocation through phase2 runner.

## Ingestion and Knowledge Corpus Pipeline
- `ingestion/v1/*`
  - Legacy pipeline.
- `ingestion/v2/src/*`
  - Async pipeline with extraction, chunking, embeddings, queueing, and optional DB backends.
  - Includes Redis queue implementation and Postgres/pgvector adapters.
- `ingestion/v2/data/*`, `ingestion/v2/rag_storage/*`
  - Generated chapter/chunk/embedding artifacts.

## API/Analytics Surface
- `hse/analytics_server.py`
  - Lightweight Flask + SSE server for streaming analytics telemetry.

## Testing and Verification Surface
- `tests/*`
  - Mixed unit/integration/verification scripts.
  - Includes async ingestion tests, persona behavior tests, benchmark-related validations.
- `tests/verification/*`
  - Generated verification reports and consolidated documentation snapshots.
