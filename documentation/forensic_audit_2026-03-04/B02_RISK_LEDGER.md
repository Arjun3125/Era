# B02 Risk Ledger (Repository-Wide)

## Data Integrity Risks
- Invalid JSON corpus files detected:
  - `ingestion/data/ministers/adaptation/principles.json`
  - `ingestion/data/ministers/adaptation/rules.json`
  - `ingestion/data/ministers/optionality/principles.json`
  - `ingestion/data/ministers/Personal Development/warnings.json`
  - `ingestion/data/ministers/psychology/principles.json`
- Impact:
  - Downstream retrieval/training/indexing can silently skip or partially ingest minister doctrine.
  - Principle coverage and KIS behavior may become inconsistent across runs.

## Runtime Reliability Risks
- Fallback-permitted paths remain available depending on environment toggles:
  - `persona/ollama_runtime.py` uses non-fatal markers unless fail-fast is enabled.
  - `run_benchmark.py` sets `SKIP_OLLAMA_CHECK=1` by default.
- Impact:
  - Research runs can accidentally include degraded/no-LLM outputs unless strict env discipline is enforced.

## Security and Deployment Risks
- Public bind without auth in analytics server:
  - `hse/analytics_server.py` enables CORS and binds `0.0.0.0`.
- Localhost endpoint assumptions hardcoded in multiple runtime and test modules.
- Impact:
  - Accidental exposure in non-local deployments.
  - Fragility across environments and containerized setups.

## Repository Hygiene and Reproducibility Risks
- Large amount of generated artifacts tracked in working tree (`evaluation/results`, ingestion artifacts, logs).
- Potentially stale/duplicate top-level result files mirror those in `evaluation/results`.
- Impact:
  - Baseline ambiguity and noisy diffs.
  - Increased chance of interpreting stale result sets.

## Architectural Complexity Risks
- Multiple active pathways exist for similar concerns:
  - Legacy ingestion v1 + async ingestion v2.
  - KIS1 + KIS2.
  - strict + semantic scorer modes.
  - static + learned uncertainty thresholds.
- Impact:
  - High combinatorial state space; difficult to guarantee experiment parity unless all knobs are frozen.

## Testing Reliability Risks
- Test suite includes mixed script-like checks and pytest tests.
- Coverage appears broad but uneven in formal assertions across core runtime orchestration paths.
- Impact:
  - Regressions in orchestration policy or evaluation glue may not be caught early by deterministic CI gates.
