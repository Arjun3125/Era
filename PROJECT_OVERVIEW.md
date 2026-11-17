# ERA — Emergent Reasoning Architecture
## Project Overview

---

## What ERA Is

ERA is a **self-improving AI advisor** built in Python 3.11/FastAPI. It acts as a personal decision-making council: when you describe a problem, 5–18 specialist "ministers" each deliberate in their own voice (using doctrine YAML personas + a local LLM), vote on a recommendation, and a "Prime Confident" sovereign makes the final call. Every turn is remembered, outcomes feed back into minister confidence weights, and the whole system gets sharper with use.

---

## Two Entry Points

| Entry | File | When to use |
|---|---|---|
| **HTTP API** | `api.py` | Production — FastAPI server on port 8765 |
| **CLI loop** | `persona/main.py` | Interactive terminal session with full REPL |

Both reach the same underlying engine. `api.py` is the primary interface; `persona/main.py` adds synthetic-human simulation and richer terminal output.

---

## Architecture Layers (top → bottom)

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRY POINTS                                                │
│  api.py (FastAPI REST)   ·   persona/main.py (CLI REPL)     │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  SITUATION LAYER  (persona/analysis.py)                      │
│  classify_situation_single_call() — single LLM call          │
│  → situation_type · domains · emotional_load · clarity       │
│  → deliberation_depth: quick / meeting / darbar              │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  KNOWLEDGE LAYER  (persona/knowledge_engine.py)              │
│  synthesize_knowledge() pulls from data/ministers/{domain}/  │
│  5-factor KIS scoring: domain · type · memory · context ·   │
│  goal. Returns ranked entries + knowledge_gaps list.         │
│  reinforce_entry() / penalize_entry() write back to JSON.    │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  COUNCIL LAYER  (modules/council_execution/engine.py)        │
│                                                              │
│  NativeCouncil.deliberate()                                  │
│    quick/war  →  keyword scoring (_NativeMinister)           │
│    meeting    →  5 ministers via MinisterVoice (LLM)         │
│    darbar     →  18 ministers, 2-round named-challenger debate│
│                                                              │
│  MinisterVoice (persona/council/minister_voice.py)           │
│    doctrine YAML → LLM system prompt → structured JSON       │
│    {stance, reasoning, confidence, warning, knowledge_cited} │
│                                                              │
│  MinisterConfidenceTracker                                   │
│  (persona/learning/minister_confidence.py)                   │
│    Bayesian weight per minister×domain (α=2, β=2 prior)      │
│    Weights applied to vote tally — consistent ministers win  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  DECISION PIPELINE  (modules/decision_pipeline/engine.py)    │
│  8-stage orchestration:                                      │
│  Input → Contract → Runtime Config → Domain Analysis →       │
│  Knowledge Synthesis → Council Routing → Council Execution → │
│  Normalization → Decision Packaging → Prime Decision         │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  SOVEREIGN LAYER  (sovereign/)                               │
│  PrimeConfident — final override, red-line enforcement       │
│  risk_threshold=0.7, vetoes council if risk too high         │
└─────────────────────────────────────────────────────────────┘
```

---

## Memory Systems (3 layers)

### 1. Episodic Memory — `persona/learning/episodic_memory.py`
- **What:** JSONL append-only log of every decision turn
- **Data:** `Episode(episode_id, turn_id, domain, user_input, recommendation, outcome, regret_score, consequence_chain, lesson_learned)`
- **Path:** `data/memory/episodes.jsonl`
- **Key methods:** `store_episode()`, `update_outcome_for_turn()`, `detect_failure_clusters()`, `detect_pattern_repetition()`
- **Wired into:** `api.py` (via `Session.feedback_loop`), `persona/main.py` (direct)

### 2. User Profiles — `persona/user_profile.py`
- **What:** Persistent cross-session user identity
- **Data:** `UserProfile(user_id, risk_tolerance, recurring_themes, total_turns, success_rate, last_active)`
- **Path:** `data/user_profiles/{user_id}.json`
- **Wired into:** `/chat` (loads on first `user_id`), `/profile/{user_id}` (GET), `build_system_context()` injects `profile_hint`

### 3. Minister Confidence — `persona/learning/minister_confidence.py`
- **What:** Bayesian per-minister×domain success tracking
- **Data:** `{minister::domain: {successes, failures}}` → weight = posterior_mean / prior_mean
- **Path:** `data/memory/minister_confidence.json`
- **Wired into:** `NativeCouncil.__init__()` (weights votes), `/feedback` (records outcomes)

---

## ML Layer — `ml/`

| Module | Role | Called from |
|---|---|---|
| `ml/ml_orchestrator.py` | 8-stage pipeline: LLM handshake → features → KIS → ML prior → outcomes | `api.py` background thread per turn |
| `ml/kis/knowledge_integration_system.py` | 5-weight KIS scoring engine | `ml_orchestrator` |
| `ml/judgment/ml_judgment_prior.py` | Learns type-weight biases from outcomes (bounded [0.7, 1.3]) | `ml_orchestrator.record_outcome()` |
| `ml/outcomes/outcome_recorder.py` | `OutcomeDatabase` JSONL + `TrainingDataGenerator` + `FeedbackIntegrator` | `ml_orchestrator` |
| `ml/labels/label_generator.py` | Generates `TypeWeights` from (success, regret) signals | `ml_orchestrator.record_outcome()` |
| `ml/features/feature_extractor.py` | `SituationState`, `ConstraintState`, `KISOutput` dataclasses | `ml_orchestrator` |
| `ml/pattern_extraction.py` | Failure trends, confidence patterns, sequential mistakes | `persona/main.py` every 100 turns |
| `ml/vector_memory.py` | FAISS semantic memory (optional, graceful fallback) | Available, not in hot path |
| `ml/reward_shaping.py` | Mode-aware reward function | `ml_orchestrator` |

**ML data paths:**
- `ml/cache/outcomes/outcome_records.jsonl` — raw outcomes
- `ml/cache/training_datasets/training_dataset_{ts}.json` — generated training sets
- `ml/models/judgment_prior_{ts}.json` — trained type-weight models

---

## Learning Feedback Loops

```
User sends feedback (POST /feedback)
  │
  ├─► reinforce_entry() / penalize_entry()
  │     Writes reinforcement_count / penalty_count back to
  │     data/ministers/{domain}/{type}s.json
  │     KIS 5-factor scoring reads these on next turn
  │
  ├─► EpisodicMemory.update_outcome_for_turn()
  │     Patches outcome field in episodes.jsonl
  │
  └─► MinisterConfidenceTracker.record_outcome()
        Updates successes/failures per minister×domain
        Next darbar/meeting uses updated Bayesian weights

Every 5 turns (background):
  OutcomeFeedbackLoop.check_and_retrain()
    Scans episodic memory for failure clusters (≥2 failures same domain+stance)
    Reduces minister.confidence_multiplier × 0.8 on repeat failures

Every turn (background thread):
  MLWisdomOrchestrator.process_decision()
    Records decision to OutcomeDatabase
    After 10 samples: trains MLJudgmentPrior
    Learned type-weight biases applied to future KIS scoring
```

---

## Four Deliberation Modes

| Mode | Ministers | Rounds | Stakes threshold |
|---|---|---|---|
| **quick** | 0 — direct LLM only | — | stakes < 0.2 |
| **war** | keyword scoring only | — | manual |
| **meeting** | 5 domain-relevant ministers | 1 LLM round | 0.2 ≤ stakes < 0.5 |
| **darbar** | 18 ministers, domain-filtered | 2 rounds: vote → named challenge | stakes ≥ 0.5 |

Stakes = `emotional_load × (1 − clarity)` — computed from `classify_situation_single_call()` each turn.

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | LLM status check |
| `POST` | `/chat` | Main conversation turn — returns `response`, `entries_used`, `deliberation_depth` |
| `POST` | `/mode` | Switch mode mid-session |
| `GET` | `/session/{id}` | Session state snapshot |
| `DELETE` | `/session/{id}` | Reset session |
| `GET` | `/sessions` | List all active sessions |
| `POST` | `/feedback` | Mark turn helpful/unhelpful → updates KIS weights + minister confidence |
| `GET` | `/profile/{user_id}` | Load persistent user profile |
| `POST` | `/export/obsidian` | Export all memory to Obsidian vault as Markdown |

---

## Obsidian Export — `persona/obsidian_exporter.py`

Set `ERA_OBSIDIAN_VAULT=C:/path/to/vault` then `POST /export/obsidian`.

Creates:
```
ERA/
├── ERA_Dashboard.md           ← Dataview queries (auto-updating tables)
├── Episodes/
│   └── turn_0001_career.md   ← one note per decision, [[wikilinks]]
├── Profiles/
│   └── {user_id}.md          ← risk tolerance, themes, success rate
└── Learning/
    ├── failure_clusters.md   ← grouped failure patterns
    ├── knowledge_gaps.md     ← domains with <5 knowledge entries (checklist)
    └── minister_confidence.md ← Bayesian weight table per minister×domain
```

---

## Key Data Directories

```
data/
├── doctrine/locked/        ← 18 minister YAML personas (speak/silent triggers)
├── ministers/{domain}/     ← principles.json, rules.json, warnings.json ...
│   └── adaptation/         ← each domain: reinforcement_count, penalty_count
├── memory/
│   ├── episodes.jsonl      ← all decision episodes (append-only)
│   ├── minister_confidence.json  ← Bayesian weights
│   └── metrics.jsonl       ← PerformanceMetrics per turn
└── user_profiles/
    └── {user_id}.json

ml/cache/
├── outcomes/               ← OutcomeDatabase JSONL
├── training_datasets/      ← generated training data
└── models/                 ← trained MLJudgmentPrior snapshots
```

---

## Supporting Systems

| System | Location | Purpose |
|---|---|---|
| **RL training** | `modules/rl/` + `decision_env/` | PPO policy training on simulated episodes — run separately |
| **Ingestion pipeline** | `ingestion/v2/` | PDF → doctrine/minister JSON — run separately |
| **Scenario memory** | `modules/scenario_memory/` | FAISS-indexed past scenarios, retrieved per turn by decision pipeline |
| **Uncertainty calibration** | `modules/uncertainty/` + `modules/calibration/` | Temperature + isotonic scaling of confidence scores |
| **Synthetic human sim** | `hse/` | Automated conversation simulation for testing |
| **Identity validator** | `persona/validation/` | Checks response for self-contradiction turn-to-turn |
| **Evaluation engine** | `modules/evaluation_engine/` | Rubric scoring, regret computation, LLM baseline comparison |

---

## Test Suite

**459 tests collected** across 30+ test files:

| File | What it covers |
|---|---|
| `test_era_upgrades.py` | All 9 upgrade tracks (23 tests) |
| `test_step4_training_data.py` | ML outcome recording → training → model |
| `test_uncertainty_calibration.py` | Temperature, isotonic, risk model |
| `test_no_legacy_pipeline_imports.py` | Architectural import guard |
| `test_runtime_config_*.py` | Runtime config engine |
| `test_scenario_memory_*.py` | Scenario embedding and retrieval |
| `test_rl_components.py` | PPO components |
| `test_decision_env.py` | Decision simulation environment |

---

## How to Run

```bash
# HTTP API
uvicorn api:app --reload --port 8765

# CLI interactive
python -m persona.main

# Export memory to Obsidian
curl -X POST http://localhost:8765/export/obsidian \
  -H "Content-Type: application/json" \
  -d '{"vault_path": "C:/Users/naren/Documents/MyVault"}'

# Submit feedback (closes learning loop)
curl -X POST http://localhost:8765/feedback \
  -H "Content-Type: application/json" \
  -d '{"session_id":"...", "turn":3, "helpful":true, "entries_used":[...]}'
```

---

## Connectivity Status

- **Total source files:** ~288
- **Reachable from api.py or persona/main.py:** ~145
- **Intentionally separate (scripts, training, ingestion):** ~50
- **Dead code:** 0 — all root stubs serve tests or the ingestion pipeline
- **Tests:** 459 collected
