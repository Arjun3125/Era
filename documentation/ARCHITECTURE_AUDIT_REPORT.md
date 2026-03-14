# ERA Architectural Audit Report

Date: 2026-03-11
Scope: Full repository static audit (structure, connectivity, dead code, pipeline integrity).

## Executive Summary
- Core decision pipeline is coherent and connected through `DecisionPipelineEngine` and stage modules.
- Evaluation and experiment infrastructure are integrated and reproducible.
- Major integrity issue was duplication in simulation environments and legacy evaluation script; safe removals applied.
- Remaining risk is RL duplication (policy gradient vs PPO) and optional modules controlled only by routing context.

## Phase 1 — Repository Structure Audit
Top-level directories:
- core/: orchestrator, contracts, observability
- modules/: pipeline stages, models, routers, controllers, evaluation, RL utilities
- decision_env/: stateful and long-horizon decision environment
- training_loop/: simulation → train → evaluate loop + RL entrypoints
- era_benchmark/: benchmark dataset and splits
- experiments/: experiment runner, scheduler, metrics/plots
- scripts/: CLI utilities for benchmark, training, calibration
- documentation/: system overview, benchmark docs, paper draft
- knowledge/: principles store for knowledge synthesis

Detected architecture layers:
- Decision environment: decision_env/
- Learning models: modules/policy_model, modules/value_model, modules/council_learning
- Council routing: modules/council_router, modules/expert_router, modules/moe_router
- Reasoning control: modules/mode_controller, modules/reasoning_controller
- Evaluation engine: modules/evaluation_engine + experiments/
- Benchmark system: era_benchmark/
- Retrieval: modules/scenario_memory
- Calibration/uncertainty: modules/calibration, modules/uncertainty
- RL: modules/rl (PPO), training_loop/rl (PG)

## Phase 2 — Module Connectivity Analysis
Primary runtime flow:
- run_refactored.py → DecisionPipelineEngine
- DecisionPipelineEngine stages:
  input_normalization → runtime_config → domain_analysis → mode_routing → scenario_memory → knowledge_synthesis →
  council_execution → council_normalization → prime_decision → decision_packaging → contract_validation

Evaluation flow:
- modules/evaluation_engine/runner.py → DecisionPipelineEngine + DecisionSimulator + Policy/Value predictors
- experiments/run_benchmark.py aggregates metrics, plots, failure analysis

Routing and control:
- council_router/module.py consumes mode_controller, reasoning_controller, expert_router, moe_router, council_learning
- outputs: reasoning_budget, selected_ministers, expert_weights

Learning + training:
- training_loop/run_loop.py orchestrates simulation, training scripts, evaluation
- training_loop/run_ppo.py uses modules/rl PPO over decision_env LongHorizonDecisionEnvironment
- training_loop/run_rl.py uses training_loop/rl PG over decision_env MultiStepDecisionEnvironment

Retrieval:
- scenario_memory module augments routing_context.extra_context for knowledge_synthesis

## Phase 3 — Dead Code Detection
SAFE_TO_REMOVE (removed in this change):
- modules/decision_environment/ (unused duplicate of decision_env)
- evaluation/evaluate_benchmark.py (legacy evaluator)
- knowledge/embeddings.npy (unused artifact)

POSSIBLY_DEPRECATED (needs decision):
- training_loop/rl (simple PG) vs modules/rl (PPO)

REQUIRED:
- All pipeline stages in DecisionPipelineEngine
- decision_env/ (used by simulation + RL entrypoints)
- modules/decision_simulator (used in evaluation engine)

## Phase 4 — Pipeline Flow Verification
Verified ordered pipeline stages and data contracts.
- Scenario memory updates routing_context and feeds knowledge_synthesis.
- Mode routing outputs selected_ministers + reasoning_budget.
- Council metrics influence decision scoring in evaluation/decision engines.
- Prime decision and packaging output final decision contract.

No accidental bypasses found; optional modules are enabled via routing_context.

## Phase 5 — Configuration Consistency
Consistent:
- experiments/run_benchmark.py uses dataset spec, routing_context, model paths
- calibration uses routing_context keys (temperature + isotonic)

Gaps:
- runtime_config overrides exist but are not surfaced via CLI (only env or injected config).
- router/controller enablement relies on routing_context JSON or file.

## Phase 6 — Experiment Infrastructure Audit
- Experiments and scheduler are reproducible and log metrics consistently.
- Failure analysis traces and reports are emitted per run.

## Phase 7 — Reinforcement Learning Integrity
- PPO stack (modules/rl) uses GAE + clipped updates; environment returns (state, reward, done, info).
- PG stack (training_loop/rl) uses advantage = return - value baseline.

Mismatch risk: two RL implementations with different configs and feature pipelines.

## Phase 8 — Performance & Redundancy
- Evaluation runs pipeline per option; expensive but mitigated by policy top-k.
- Scenario memory embedding can be heavy; caching exists.
- Redundant environment/RL stacks were the main structural redundancy.

## Phase 9 — System Coherence Check
- Modular and layered design is consistent.
- Key gaps are duplication of RL and environment stacks, and routing configuration discoverability.

## Phase 10 — Recommendations
Immediate (safe):
1. Keep decision_env as the single environment stack (done).
2. Remove legacy evaluator (done).
3. Remove unused embeddings artifact (done).

Next decisions:
1. Choose one RL stack (PPO recommended) and deprecate the other.
2. Add CLI flags for key routing toggles (expert_router, moe_router, controllers).
3. Consider caching knowledge_synthesis per option to reduce repeated pipeline work.

## Actions Executed in This Pass
- Removed modules/decision_environment/
- Removed evaluation/evaluate_benchmark.py
- Removed knowledge/embeddings.npy

