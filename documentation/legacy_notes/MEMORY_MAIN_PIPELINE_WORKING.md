# Memory Module Contribution to Main Pipeline

## Short Answer
Yes, `Memory` can contribute to the main pipeline, but currently it behaves like a standalone prototype module and is not directly wired into active runtime/evaluation flows.

## What `Memory` Does Today

`C:\era\Memory` contains a Personal World Model (PWM) memory prototype with:
- Prompt-template-driven memory extraction and commit gating logic (`Memory/pwm.py`).
- SQL schema for structured memory graph and governance (`Memory/schema.sql`).
- Prompt templates for each stage (`Memory/templates/*`).

## Functional Breakdown

## 1) Pipeline Helpers (`Memory/pwm.py`)
Provides lightweight functions for an extract -> score -> commit flow:
- `session_summary(llm, conversation_text)`
- `extract_signals(llm, session_summary_json)`
- `generate_hypotheses(llm, observations_json)`
- `score_confidence(llm, hypotheses_json)`
- `decide_commits(llm, calibrated_hypotheses_json, threshold=0.7)`
- `translate_to_db_changes(approved_decisions_json)`

Behavior details:
- Uses prompt templates from `Memory/templates`.
- Calls `llm.analyze` / `llm.speak` / `llm.generate` if available.
- Fails defensively (returns safe defaults instead of crashing).
- Contains simple fallback auto-decisioning for commit/hold/reject by confidence.

## 2) Memory Schema (`Memory/schema.sql`)
Defines relational/graph-like memory tables for:
- Identity layer: `users`, `global_identity`
- Entity layer: `entities`, `people`, `projects`, `events`
- Relationship graph: `relationships`, `relationship_timeline`
- Evidence/inference: `observations`, `inferences`
- Session/governance: `sessions`, `session_summaries`, `memory_changes`

It is a governance-oriented schema with confidence fields, lifecycle tracking, and change approval hooks.

## 3) Prompt Templates (`Memory/templates/*`)
Prompt assets for each PWM stage:
- `session_summary.txt`
- `signal_extraction.txt`
- `hypothesis_generation.txt`
- `confidence_scoring.txt`
- `commit_decision.txt`
- `memory_write.txt`

These are intended to standardize LLM prompts per memory stage.

## Current Integration Status (Non-Document Reference Audit)

Active pipeline references to `Memory/*` are minimal:
- `Memory/pwm.py` is not imported by main runtime/evaluation modules.
- `Memory/schema.sql` is not applied by current runtime code.
- No direct references from:
  - `evaluation/run_phase2_robustness.py`
  - `run_benchmark.py`
  - `system_main.py`

Related active memory systems exist elsewhere:
- `persona/learning/episodic_memory.py`
- `ml/vector_memory.py`
- `ingestion/v2/src/memory_db.py`

Conclusion:
- `Memory` is currently a prototype/staging memory subsystem.
- Not a hard dependency in the active mainline run path.

## How It Can Contribute to Main Pipeline

Use `Memory` as a controlled write-governance layer without replacing existing memory systems.

Recommended contribution pattern:
1. Keep existing runtime decision path unchanged.
2. After each evaluated conversation/session, call `Memory/pwm.py` helpers to generate memory candidates.
3. Use `decide_commits(...)` as gate policy for memory writes.
4. Map approved hypotheses via `translate_to_db_changes(...)`.
5. Persist into one selected backend (either this SQL schema or existing `ingestion/v2/src/memory_db.py` abstraction).
6. Feed approved memory signals back into retrieval/KIS pathways.

## Safe Integration Plan

Phase 1 (Shadow mode):
- Run PWM extraction alongside runtime, write only audit logs (no DB commit).
- Compare with current episodic memory outputs.

Phase 2 (Controlled commit):
- Enable commit gate for high-confidence changes only.
- Record all accepted/rejected memory actions.

Phase 3 (Operational integration):
- Expose memory retrieval API consumed by persona/sovereign/evaluation.
- Add regression tests for memory consistency and drift.

## Risks If Integrated Naively
- Duplicate memory systems with conflicting truth sources.
- Inconsistent schemas between `Memory/schema.sql` and `ingestion/v2/src/memory_db.py`.
- Uncalibrated commit thresholds causing noisy memory growth.

## Bottom Line

`Memory` can contribute meaningfully to the main pipeline as a structured memory-governance and commit-gating subsystem. At present, it is not directly integrated; contribution requires explicit wiring into post-decision/session processing and alignment with existing memory backends.
