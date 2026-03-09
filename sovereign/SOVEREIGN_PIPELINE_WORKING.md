# Sovereign Package - Working and Main Pipeline Contribution

## Scope
This document describes what `C:\era\sovereign` does, where it is used in the current codebase, and how it can contribute to the main pipeline without breaking existing flows.

## What `sovereign/` currently provides

### 1) `PrimeConfident` final decision authority
- File: `sovereign/prime_confident.py`
- Core methods:
  - `PrimeConfident.__init__` (line ~19)
  - `_analyze_emotional_distortion` (line ~29)
  - `_detect_pattern_recurrence` (line ~44)
  - `decide(...)` (line ~86)
- Behavior:
  - Applies doctrine-aware constraints and checks for emotional distortion / recurring bad patterns.
  - Uses council recommendation + minister outputs to return final outcome (`accept`, `defer`, etc.).
  - Optionally adds LLM viability assessment if adapter is present.

### 2) LLM adapter wrapper with fallback
- File: `sovereign/llm_adapter.py`
- Core methods:
  - `generate(...)`
  - `summarize(...)`
  - `evaluate_viability(...)`
- Behavior:
  - Wraps `persona.ollama_runtime.OllamaRuntime` if available.
  - Falls back to stub/heuristic behavior when runtime is unavailable.

### 3) Independent/legacy-style orchestration paths
- Files:
  - `sovereign/runtime/council_runtime.py`
  - `sovereign/council/aggregator.py`
  - `sovereign/ministers/orchestrator.py`
  - `sovereign/sovereign_main.py`
- Behavior:
  - Provide standalone council/minister runtime patterns.
  - Useful for demos and alternative orchestration experiments.
  - Not the primary path used by Phase2/Phase3 evaluation pipeline.

## Where `sovereign/` is used in the main pipeline

## Active integrations (real)

### `system_main.py`
- Imports `PrimeConfident`:
  - `system_main.py:47`
- Instantiates and uses it in the runtime object:
  - `system_main.py:114-115`

### `persona/main.py`
- Imports `PrimeConfident`:
  - `persona/main.py:35`
- Uses `prime.decide(...)` inside MCA decision loop:
  - `persona/main.py:128` (MCA loop definition)
  - `persona/main.py:232-243` (prime decision call)
- Uses `sovereign.llm_adapter.OllamaAdapter` as fallback when `OllamaRuntime` init fails:
  - `persona/main.py:340-353`

## Test references
- `tests/test_features.py:19`
- `tests/verify_api_fixes.py:41`

## What is NOT primary pipeline today
- `sovereign/sovereign_main.py` is more simulation/demo-oriented.
- `sovereign/runtime/*`, `sovereign/council/aggregator.py`, and much of `sovereign/ministers/*` are not the canonical evaluation execution path.

## Can `sovereign/` contribute more to main pipeline?
Yes.

The package already contributes through `PrimeConfident` and fallback adapter. It can contribute further by making its stronger orchestration features consumable by `persona/main.py` and `evaluation/*` under controlled flags.

## Practical contribution plan

### Step 1 (safe): expose stable integration interface
- Add a single entry service in `sovereign/` (for example `sovereign/integration.py`) that exposes:
  - `run_prime_decision(council_recommendation, minister_outputs, context)`
  - `evaluate_viability(text)`
- Keep current `PrimeConfident` internals unchanged.
- Objective: remove direct scattered coupling and give one stable integration point.

### Step 2 (safe): optional strategy switch in persona loop
- In `persona/main.py`, add a config switch:
  - default path remains current.
  - optional path calls `sovereign` integration service for final decision package.
- Log both decisions in shadow mode first (no behavior change), then compare.

### Step 3 (evaluation-compatible): wire shadow metrics
- Add fields into evaluation metadata:
  - `prime_decision_source` (`legacy_persona` vs `sovereign_service`)
  - disagreement indicator between two decision sources.
- Keep scorer and calibration unchanged while validating behavior parity.

### Step 4 (controlled adoption): gate-based promotion
- Promote sovereign-driven finalizer only if:
  - no core regression,
  - stress/OOD stability preserved,
  - calibration not degraded.

## Risks to manage
- `sovereign/llm_adapter.py` has fallback behavior that can hide runtime failures in research mode.
  - In evaluation paths, enforce fail-fast runtime policy.
- Avoid replacing both council + prime logic at once.
  - Introduce one layer at a time.

## Recommended current status
- Treat `PrimeConfident` as active and critical.
- Treat sovereign orchestration modules as experimental/secondary until explicitly integrated into phase runners.

## Quick summary
- `sovereign/` is already part of main runtime via `PrimeConfident`.
- It can contribute more by providing a unified integration service and shadow-mode evaluation before promotion.
