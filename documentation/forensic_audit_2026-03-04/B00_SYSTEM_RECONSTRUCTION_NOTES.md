# B00 System Reconstruction Notes

## Evidence Set Used
- `documentation/forensic_audit_2026-03-04/A00_SCOPE_AND_METHOD.md`
- `documentation/forensic_audit_2026-03-04/A01_FILE_COVERAGE.md`
- `documentation/forensic_audit_2026-03-04/A02_PYTHON_ARCHITECTURE_INDEX.md`
- `documentation/forensic_audit_2026-03-04/A03_PARSER_AND_DATA_QUALITY_FLAGS.md`
- `documentation/forensic_audit_2026-03-04/A04_DEPENDENCY_AND_ENTRYPOINT_MAP.md`
- `documentation/forensic_audit_2026-03-04/A05_API_SECURITY_TEST_SURFACE.md`
- `documentation/forensic_audit_2026-03-04/A06_documentation_index.json`

## Project Identity Inference
- The repository centers on an "ERA" sovereign decision architecture where a council of ministers plus orchestrated execution modes produce decisions under uncertainty.
- Primary proof points:
  - `README.md` and runtime entrypoints (`system_main.py`, `persona/main.py`, `run_benchmark.py`) describe and implement council-based multi-perspective decisioning.
  - `persona/ministers.py` defines domain ministers and judges, implying structured expert decomposition rather than a single-model assistant.
  - `evaluation/run_phase2_robustness.py` and related artifacts in `evaluation/results/` show intensive benchmark-gated experimentation.
- Industry/domain positioning: AI decision-support research platform with governance, robustness, and evaluation instrumentation. It is not a pure web SaaS product; the center of gravity is offline/CLI experimentation and architecture validation.

## Architecture Style Inference
- Hybrid monolith with modular packages:
  - Runtime decision engine: `persona/`, `sovereign/`, `ml/`.
  - Evaluation harnesses and gates: `evaluation/`.
  - Knowledge ingestion and retrieval pipelines: `ingestion/v1`, `ingestion/v2`.
  - Support test harnesses and verification docs: `tests/`, `tests/verification/`.
- Not microservices: there is no service mesh, no independent deploy units, and no API gateway topology.
- Internal orchestration is Python-process-local, with optional external model endpoint dependency (Ollama HTTP).

## Core Execution Paths
- Runtime interactive path:
  - `system_main.py` and `persona/main.py` initialize runtime, council, mode orchestrator, and learning components.
  - `persona/ollama_runtime.py` provides LLM calls and failure-mode handling (`SKIP_OLLAMA_CHECK`, `EVAL_FAIL_FAST_ERRORS`).
- Evaluation path:
  - `run_benchmark.py` and `evaluation/run_phase2_robustness.py` execute baseline/council comparisons with per-scenario scoring.
  - `evaluation/run_phase2_with_gates.py` acts as wrapper with preflight daemon health check (`assert_ollama_available`).
- Stress/governance path:
  - `evaluation/run_phase4_stress.py` invokes the phase2 runner with stress switches rather than creating a separate incompatible harness.

## Measurement and Scoring Observations
- Scoring is explicitly rubric-centric with path + principle factors in `evaluation/scoring/outcome_scorer.py`.
- Principle matching mode is environment-controlled via `EVAL_PRINCIPLE_MATCH_MODE` and supports strict/semantic variants.
- The existence of strict and semantic paths in the scorer materially affects interpretation of architecture quality.

## Uncertainty and Control Layer Observations
- `persona/modes/mode_orchestrator.py` contains policy thresholds and linear uncertainty composition logic.
- `evaluation/learned_uncertainty.py` introduces frozen learned predictor integration.
- `evaluation/run_phase2_robustness.py` implements runtime-percentile threshold probing and a second pass for escalation, resolving absolute-threshold fragility.

## KIS2 and Retrieval Layer Observations
- `evaluation/kis2_retrieval.py` integrates embedding retrieval with optional reranker.
- `evaluation/run_phase2_robustness.py` includes KIS2 activation modes (`always`, `uncertainty_percentile`) and uncertainty-gated retrieval trigger logic.
- This confirms the architecture now supports controlled parallel experimentation (KIS1/KIS2 behavior) without fully replacing legacy paths.

## API and Service Surface
- Minimal external API surface exists: `hse/analytics_server.py` with `/` and `/stream` routes.
- Most critical operations run as scripts/CLI entrypoints, not authenticated HTTP APIs.

## Data and Artifact Footprint
- Repository includes large corpus artifacts and generated outputs (`data/books`, `ingestion/v2/data`, `evaluation/results`).
- The project is artifact-heavy and doubles as a research log store; this has implications for reproducibility and repository hygiene.

## Initial Risk Signals
- Invalid JSON files in ingestion minister datasets are recorded in `A03_PARSER_AND_DATA_QUALITY_FLAGS.md`.
- Runtime behavior includes optional silent fallback patterns in some paths unless fail-fast env is set.
- Localhost defaults and open host bind patterns are present (`A05_API_SECURITY_TEST_SURFACE.md`).
- Significant amount of generated result files are in-repo, which complicates deterministic baselines and change review.
