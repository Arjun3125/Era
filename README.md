# ERA

ERA is a refactored, local decision-governance pipeline built around a single staged orchestrator. The active repository is the lean refactor path, not the older multi-subsystem platform that some retained docs still describe.

## What It Does

Given a user prompt, ERA:

1. normalizes the request and routing context
2. resolves runtime settings
3. analyzes the problem domain
4. selects a reasoning mode
5. synthesizes local knowledge
6. runs a minister-style council when needed
7. normalizes council output
8. produces a final decision
9. packages the result
10. validates inter-stage contracts and emits telemetry

The main runtime is CLI-first and returns structured JSON.

## Current Entry Points

- [`run_refactored.py`](c:\era\run_refactored.py): primary CLI entrypoint
- [`system_main.py`](c:\era\system_main.py): compatibility shim that delegates to `run_refactored.py`

## Quick Start

```bash
cd c:\era
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python run_refactored.py --input "Should we delay the release for compliance review?"
```

Interactive mode:

```bash
python run_refactored.py
```

Compatibility entrypoint:

```bash
python system_main.py --input "Need a decision on vendor risk"
```

## Supported Modes

- `quick`
- `meeting`
- `war`
- `darbar`

Example:

```bash
python run_refactored.py --input "We need a final high-stakes ruling" --mode darbar
```

## Embedded Decision Environment

ERA now includes an embedded one-step decision environment that treats the refactored
pipeline as the acting policy over generated scenarios.

Run a short simulation batch:

```bash
python run_refactored.py --simulate-episodes 3 --scenario-domain startup --seed 7
```

Optional experience log:

```bash
python run_refactored.py --simulate-episodes 5 --experience-log logs/decision_env_episodes.jsonl
```

Benchmark ERA against ERA-Bench:

```bash
python evaluation/evaluate_benchmark.py --limit 20 --mode meeting
```

Full evaluation engine CLI:

```bash
python scripts/run_benchmark.py --benchmark era_benchmark --mode meeting
```

Learning-layer hybrid decision (policy + value + reasoning):

```bash
python scripts/run_benchmark.py \
  --benchmark era_benchmark \
  --decision-policy hybrid_all \
  --policy-model data/policy_model/model_v1_1_logistic \
  --value-model data/value_model/model_v1_1_ridge
```

Expert router (Mixture-of-Experts council):

```bash
python run_refactored.py \
  --input "Competitor undercut pricing" \
  --mode meeting \
  --routing-context "{`"expert_router_enabled`": true, `"expert_router_top_k`": 3}"
```

Learned minister weights (council_weight_model):

```bash
python run_refactored.py \
  --input "Should we acquire a rival?" \
  --mode meeting \
  --routing-context "{`"council_weight_model_enabled`": true, `"council_weight_top_k`": 4, `"council_weight_model_path`": `"data/council_learning/model`"}"
```

Generate simulated outcomes (decision environment):

```bash
python scripts/generate_simulated_data.py --scenarios-root era_benchmark --limit 300 --output data/simulated/decision_env.jsonl
```

Regenerate ERA-Bench (v1.1) with balanced, context-driven labels:

```bash
python scripts/generate_era_benchmark.py --root era_benchmark --seed 20260310
```

## Repository Layout

- [`config/`](c:\era\config): runtime settings and override normalization
- [`core/`](c:\era\core): contracts, orchestrator, observability primitives
- [`decision_env/`](c:\era\decision_env): scenario generation, simulation, reward shaping, and episode execution around the refactored ERA policy
- [`era_benchmark/`](c:\era\era_benchmark): ERA-Bench scenarios (structured decision cases) plus schema and index for evaluation/training seeds
- [`scripts/`](c:\era\scripts): benchmark runners and dataset generators (including ERA-Bench regeneration)
- [`modules/`](c:\era\modules): pipeline stage implementations
- [`modules/learning_core/`](c:\era\modules\learning_core): shared feature extraction and dataset utilities for learning models
- [`modules/decision_environment/`](c:\era\modules\decision_environment): scenario simulation + reward computation for learned training loops
- [`data/`](c:\era\data): retained local data and artifacts
- [`knowledge/`](c:\era\knowledge): principle corpus used by knowledge synthesis
- [`tests/`](c:\era\tests): unit and integration coverage for the refactored runtime
- [`documentation/`](c:\era\documentation): technical docs, retained audits, cleanup notes

## Key Files

- [`modules/decision_pipeline/engine.py`](c:\era\modules\decision_pipeline\engine.py): central 10-stage pipeline composition
- [`core/orchestrator/runtime.py`](c:\era\core\orchestrator\runtime.py): generic synchronous stage runner
- [`core/contracts/io.py`](c:\era\core\contracts\io.py): typed contracts for inter-stage data flow
- [`config/settings.py`](c:\era\config\settings.py): environment settings and invariants

## Observability

Observability is optional and controlled by environment variables:

- `ERA_OBS_ENABLED`
- `ERA_OBS_EMIT_EVENTS`
- `ERA_OBS_EMIT_SUMMARY`
- `ERA_OBS_WRITE_FILE`
- `ERA_OBS_STDERR`
- `ERA_OBS_FILE`

Default file target:

- `logs/orchestration_events.jsonl`

## Testing

Focused smoke:

```bash
python run_refactored.py --input "Need a release decision"
```

Focused runtime tests:

```bash
pytest tests/test_decision_pipeline_engine.py tests/test_no_legacy_pipeline_imports.py tests/test_decision_env.py -q
```

Broader refactor-era suite:

```bash
pytest tests/test_config_settings.py tests/test_contracts_*.py tests/test_domain_analysis.py tests/test_knowledge_synthesis.py tests/test_council_execution.py tests/test_council_normalization.py tests/test_prime_decision.py tests/test_decision_pipeline_engine.py -q
```

## Documentation

Start here for the current repository:

- [`documentation/REPOSITORY_TECHNICAL_GUIDE.md`](c:\era\documentation\REPOSITORY_TECHNICAL_GUIDE.md)

Important note:

- Several older docs in [`documentation/`](c:\era\documentation) and [`tests/README.md`](c:\era\tests\README.md) still describe removed legacy subsystems. Treat the technical guide above plus `config/`, `core/`, `modules/`, and current tests as the source of truth.

## Current Limitations

- `requirements.txt` still contains more dependencies than the active runtime needs
- some retained docs are stale
- the active runtime is CLI and Python API only; there is no current web UI or active HTTP API path on `main`

## Development

If you extend the system:

1. work inside `config/`, `core/`, or `modules/`
2. prefer adding behavior as a pipeline stage or extension stage
3. update tests with the change
4. update the technical guide when architecture or usage changes
