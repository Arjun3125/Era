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

- [`api.py`](api.py): primary HTTP API server (FastAPI, port 8765)
- [`persona/main.py`](persona/main.py): CLI interactive loop with synthetic-human simulation
- [`run_refactored.py`](run_refactored.py): CLI single-shot decision pipeline
- [`system_main.py`](system_main.py): compatibility shim that delegates to `run_refactored.py`

## Quick Start

```bash
cd C:\Users\naren\Work\Projects\School\era
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

HTTP API:

```bash
uvicorn api:app --reload --port 8765
```

CLI interactive:

```bash
python -m persona.main
```

CLI single-shot:

```bash
python run_refactored.py --input "Should we delay the release for compliance review?"
```

## LLM Providers

Three runtime options, selected at startup:

- `ERA_LLM_PROVIDER=opencode_server` — local OpenCode server (free-tier models, no API key)
- `OPENROUTER_API_KEY` set — OpenRouter cloud models
- neither — local Ollama via `sovereign.llm_adapter.OllamaAdapter`

OpenCode setup — one command:

```powershell
.\scripts\run_opencode.ps1
```

It starts `opencode serve` on port 9467 with a generated password, wires the
environment, and launches the API on port 8765. To start the pieces by hand:

```powershell
$env:OPENCODE_SERVER_PASSWORD="<password>"
opencode serve --port 9467 --hostname 127.0.0.1
# in another shell:
$env:ERA_LLM_PROVIDER="opencode_server"
$env:OPENCODE_SERVER_URL="http://127.0.0.1:9467"
$env:OPENCODE_SERVER_PASSWORD="<password>"
$env:OPENCODE_MODEL="deepseek-v4.1-flash-free"
```

Direct HTTP calls to the OpenCode free tier are rejected; the adapter goes through
the official server session API (`persona/opencode_runtime.py`). The server must
run with plugins disabled or it can crash on generation, so start it with a clean
config directory plus `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`.

### When the free quota runs out

Completed LLM calls are cached in `data/llm_cache/` and the failed turn is queued
in `data/llm_queue/`. `/chat` returns HTTP 503 with `quota_exhausted: true` and a
`queued_job` id. After the quota resets, `POST /resume` (or the background retry,
every 15 minutes by default) replays the turn: cached minister calls cost nothing,
only unfinished calls run. A resumed turn continues from the failed call instead
of restarting the council.

```bash
curl -X POST http://127.0.0.1:8765/resume
```

Tune with `ERA_LLM_CACHE_TTL_SECONDS` (0 disables caching) and
`ERA_RESUME_INTERVAL_SECONDS` (0 disables automatic retry).

## Supported Modes

- `quick`
- `meeting`
- `war`
- `darbar`

Example:

```bash
python run_refactored.py --input "We need a final high-stakes ruling" --mode darbar
```

## Repository Layout

- [`config/`](config): runtime settings and override normalization
- [`core/`](core): contracts, orchestrator, observability primitives
- [`modules/`](modules): pipeline stage implementations
- [`persona/`](persona): knowledge engine, minister voice, user profiles, episodic memory
- [`data/`](data): minister JSON files, doctrine YAMLs, memory stores
- [`tests/`](tests): 87 test files, 459 tests
- [`documentation/`](documentation): technical docs, retained audits, cleanup notes

## Key Files

- [`modules/decision_pipeline/engine.py`](modules/decision_pipeline/engine.py): central 10-stage pipeline composition
- [`modules/council_execution/engine.py`](modules/council_execution/engine.py): NativeCouncil with LLM minister voice
- [`persona/knowledge_engine.py`](persona/knowledge_engine.py): KIS scoring, Chroma retrieval, reinforce/penalize
- [`persona/council/minister_voice.py`](persona/council/minister_voice.py): LLM-per-minister deliberation
- [`persona/learning/episodic_memory.py`](persona/learning/episodic_memory.py): decision episode storage
- [`persona/learning/minister_confidence.py`](persona/learning/minister_confidence.py): Bayesian weight tracking
- [`persona/user_profile.py`](persona/user_profile.py): persistent cross-session user identity
- [`persona/context.py`](persona/context.py): system context builder
- [`config/settings.py`](config/settings.py): environment settings and invariants
- [`api.py`](api.py): FastAPI HTTP server with all endpoints

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

ERA fix + upgrade tests (34 tests):

```bash
pytest tests/test_era_fixes.py tests/test_era_upgrades.py -v
```

Focused pipeline tests:

```bash
pytest tests/test_decision_pipeline_engine.py tests/test_no_legacy_pipeline_imports.py -q
```

Full test suite (459 tests):

```bash
pytest tests/ -v
```

## Documentation

Start here for the current repository:

- [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md): architecture, memory systems, API endpoints, learning loops
- [`documentation/REPOSITORY_TECHNICAL_GUIDE.md`](documentation/REPOSITORY_TECHNICAL_GUIDE.md): repo structure, modules, contribution guide

Completed task tracking:

- [`ERA_FIX_PLAN.md`](ERA_FIX_PLAN.md): 6 bug fixes (all complete)
- [`ERA_UPGRADE_PLAN.md`](ERA_UPGRADE_PLAN.md): 9 upgrade tracks (all complete)

Important note:

- Several older docs in [`documentation/legacy_notes/`](documentation/legacy_notes) still describe removed legacy subsystems. Treat the documents above as the source of truth.

## Current Limitations

- `requirements.txt` still contains more dependencies than the active runtime needs
- some retained docs in `documentation/legacy_notes/` are stale
- no authenticated service layer or web UI yet

## Development

If you extend the system:

1. work inside `config/`, `core/`, or `modules/`
2. prefer adding behavior as a pipeline stage or extension stage
3. update tests with the change
4. update the technical guide when architecture or usage changes
