# 03_FILE_REFERENCE.md

# 📁 Era Project - Complete File Reference

**Every file in the project, organized by module, with purpose and key functions**

---

## Project Root (`C:\era\`)

### Entry Points & Scripts

| File | Purpose | Key Functions |
|------|---------|---------------|
| `persona/main.py` | **Main entry point** for Persona N conversation system | `main()`, `_mca_decision()`, mode selection |
| `run_persona_conversation.py` | Quick-start script for synthetic conversation | Wraps `persona.main` with environment setup |
| `simulation_runner.py` | Automated simulation runner for stress testing | Batch conversation execution |
| `sovereign_main.py` | Sovereign orchestrator main entry point | Full 12-system integration |
| `sovereign_main_integration_example.py` | Example integration code for sovereign orchestrator | Reference implementation |

### Configuration Files

| File | Purpose | Notes |
|------|---------|-------|
| `.env` | Environment variables | `PERSONA_DEBUG`, `AUTOMATED_SIMULATION`, model configs |
| `requirements.txt` | Python dependencies | requests, aiohttp, faiss-cpu, sentence-transformers, Flask |
| `.gitignore` | Git ignore patterns | Standard Python + venv + logs |

### Documentation (Root Level)

| File | Purpose |
|------|---------|
| `SYSTEM_STATUS.md` | Complete system verification summary |
| `SYSTEM_READY.md` | Quick-start guide for synthetic conversation |
| `MODE_ORCHESTRATOR_COMPLETE.md` | Mode system implementation complete |
| `MODE_SELECTION_GUIDE.md` | When to use each mode (450+ lines) |
| `MODE_QUICK_REFERENCE.md` | Quick lookup for modes and ministers |
| `MODE_EXAMPLES.md` | Real-world scenarios in all 4 modes |
| `MODE_TESTING_CHECKLIST.md` | 25 comprehensive tests |
| `DYNAMIC_COUNCIL_GUIDE.md` | How council routing works |
| `HYBRID_MEMORY_ARCHITECTURE.md` | Three-tier memory design |
| `PWM_INTEGRATION_GUIDE.md` | Personal World Model integration |
| `PWM_INTEGRATION_SUMMARY.md` | PWM implementation summary |
| `PWM_REDESIGN_IMPLEMENTATION.md` | PWM redesign details |
| `SOVEREIGN_ORCHESTRATOR_GUIDE.md` | 12-system integration guide |
| `SYNTHETIC_CONVERSATION_GUIDE.md` | Synthetic human simulation guide |
| `TESTING_VALIDATION_GUIDE.md` | Testing procedures |
| `INTEGRATION_SUMMARY.md` | Architecture integration summary |
| `DYNAMIC_COUNCIL_GUIDE.md` | Council selection logic |

### Logs & Metrics

| File | Purpose |
|------|---------|
| `live_metrics.json` | Real-time performance metrics |
| `persona_output.log` | Conversation output log |
| `run_output.log` | Simulation run output |
| `benchmark_quickstart.log` | Benchmark results |
| `ingestion_kis_full_test.log` | KIS ingestion test log |
| `test_ingestion_debug.log` | Debug logs for ingestion testing |
| `test_ingest_full_output.log` | Full ingestion test output |

---

## Module: `persona/` (Core Persona System)

### Core Files

#### `main.py` ⭐
**Purpose:** Main conversation loop and decision orchestration

**Key Functions:**
- `main()` - Entry point, initializes all systems
- `_mca_decision()` - Ministerial Cognitive Architecture decision loop
- Mode selection menu (startup)
- `/mode` command handler (mid-conversation)

**Dependencies:**
- `modes/mode_orchestrator.py`
- `council/dynamic_council.py`
- `learning/episodic_memory.py`
- `learning/performance_metrics.py`
- `ollama_runtime.py`

**Lines:** ~600+

---

#### `brain.py`
**Purpose:** High-level decision control (ask/speak/engage)

**Key Functions:**
- `assess_coherence()` - Intent detection (0.95 coherence measured)
- `analyze_situation()` - Emotional load and clarity scoring
- `classify_domain()` - Automatic domain detection and locking
- `decide_action()` - Control decision (ask/speak/engage)

---

#### `ollama_runtime.py`
**Purpose:** LLM connection layer (Ollama integration)

**Key Functions:**
- `generate()` - Call Ollama API with timeout handling
- `check_connection()` - Verify Ollama is running
- `list_models()` - Get available models

**Models Used:**
- `llama3.1:8b-instruct-q4_0` - Synthetic user
- `qwen3:14b` - Persona responses

**Timeout:** 30 seconds with graceful fallback

---

#### `context.py`
**Purpose:** Conversation context management

**Key Functions:**
- `get_context()` - Retrieve current conversation context
- `update_context()` - Add new turn to context
- `get_domain_context()` - Domain-specific context

---

#### `state.py`
**Purpose:** System state tracking

**Key Functions:**
- `get_current_mode()` - Current decision mode
- `get_turn_count()` - Total turns in conversation
- `get_domain_lock()` - Current domain lock status

---

#### `trace.py`
**Purpose:** Debug tracing and logging

**Key Functions:**
- `trace()` - Debug trace with context
- `trace_decision()` - Trace decision pipeline
- `trace_council()` - Trace council convening

---

#### `ministers.py` ⭐
**Purpose:** Definition of all 18 ministers

**Ministers Defined:**
1. Risk Minister
2. Power Minister
3. Strategy Minister (Grand Strategist)
4. Technology Minister
5. Timing Minister
6. Psychology Minister
7. Economics Minister
8. Ethics Minister
9. Relationships Minister
10. Health Minister
11. Creativity Minister
12. Spirituality Minister
13. Finance Minister
14. Career Minister
15. Family Minister
16. Education Minister
17. Environment Minister
18. Legitimacy Minister

**Each Minister Has:**
- Domain expertise
- Doctrine (principles, rules, warnings)
- Confidence scoring
- Voting logic

---

#### `council.py`
**Purpose:** Legacy council implementation (superseded by dynamic_council)

**Note:** Mostly replaced by `council/dynamic_council.py`

---

#### `knowledge_engine.py`
**Purpose:** Knowledge base loading and querying

**Key Functions:**
- `load_knowledge()` - Load minister knowledge from disk
- `query_by_domain()` - Get knowledge for specific domain
- `get_principles()` - Get foundational principles

---

#### `doctrine_loader.py`
**Purpose:** Load minister doctrines from files

**Key Functions:**
- `load_doctrine()` - Load doctrine JSON
- `validate_doctrine()` - Ensure doctrine consistency
- `get_doctrine_for_minister()` - Get specific minister's doctrine

---

#### `analysis.py`
**Purpose:** Post-decision analysis

**Key Functions:**
- `analyze_decision_quality()` - Evaluate decision quality
- `compute_confidence()` - Calculate confidence score
- `identify_improvement_areas()` - Find weak points

---

#### `clarify.py`
**Purpose:** Clarification mode (auto-switches when user is unclear)

**Key Functions:**
- `detect_clarity_need()` - Detect when clarification needed
- `generate_clarification()` - Generate clarifying questions

---

#### `persona_minister_kis_bridge.py`
**Purpose:** Bridge between Persona ministers and KIS

**Key Functions:**
- `minister_to_kis_query()` - Convert minister vote to KIS query
- `kis_to_minister_confidence()` - Update minister confidence from KIS

---

### Submodule: `persona/council/`

#### `dynamic_council.py` ⭐
**Purpose:** Mode-aware minister selection and convening

**Key Functions:**
- `select_ministers(mode, domain)` - Select relevant ministers
- `convene_council(ministers, user_input)` - Get minister recommendations
- `aggregate_recommendations()` - Combine minister votes
- `get_consensus_strength()` - Calculate agreement level

**Mode Routing:**
- QUICK: No ministers (direct LLM)
- WAR: 5 ministers (Risk, Power, Strategy, Tech, Timing)
- MEETING: 3-5 domain-relevant ministers
- DARBAR: All 18 ministers

---

### Submodule: `persona/modes/`

#### `mode_orchestrator.py` ⭐
**Purpose:** 4-mode decision routing and framing

**Key Classes:**
- `ModeOrchestrator` - Central controller
- `ModeStrategy` - Abstract base class
- `QuickModeStrategy` - 1:1 mentoring
- `WarModeStrategy` - Victory-focused
- `MeetingModeStrategy` - Balanced debate
- `DarbarModeStrategy` - Full council wisdom
- `ModeResponse` - Response metadata

**Key Functions:**
- `select_mode()` - Mode selection (startup or /mode command)
- `route_decision()` - Route based on mode
- `should_invoke_council()` - Council required for mode?
- `get_framing_prompt()` - Mode-specific system prompt
- `aggregate_results()` - Mode-specific aggregation rules

**Lines:** 450+

---

#### `mode_metrics.py`
**Purpose:** Track performance per mode

**Key Functions:**
- `record_mode_decision()` - Log mode-specific decision
- `compute_mode_success_rate()` - Success rate per mode
- `compare_modes()` - Mode performance comparison
- `report_periodic()` - Report every 100 turns

**Metrics Tracked:**
- Success rate per mode
- Average confidence per mode
- Regret scores per mode
- Turn count per mode

---

### Submodule: `persona/learning/`

#### `episodic_memory.py` ⭐
**Purpose:** Store every decision + outcome

**Key Functions:**
- `store_episode()` - Save turn data
- `find_similar_episodes()` - Pattern matching
- `get_recent_episodes()` - Recent history
- `extract_lessons()` - Learn from past

**Data Stored Per Turn:**
- Turn ID, domain, user input
- Persona recommendation
- Confidence scores
- Minister votes
- Council recommendation
- Outcome (success/failure)
- Regret score

**Format:** JSONL (one episode per line)

---

#### `performance_metrics.py` ⭐
**Purpose:** Track success rates and identify weak domains

**Key Functions:**
- `record_decision()` - Log decision with outcome
- `compute_domain_performance()` - Success rate per domain
- `detect_weak_domains()` - Find domains <50% success
- `compute_minister_adjustments()` - Guide retraining
- `report_periodic()` - Report every 100 turns

**Metrics Tracked:**
- Success rate by domain
- Minister performance
- Mode stability
- Feature coverage
- Failure clusters

---

#### `confidence_model.py`
**Purpose:** Bayesian confidence tracking per domain

**Key Functions:**
- `update_confidence()` - Bayesian update based on outcome
- `get_confidence()` - Current confidence for domain
- `decay_confidence()` - Time-based decay
- `recover_confidence()` - Recovery after success

---

#### `consequence_engine.py`
**Purpose:** Simulate forward ripple effects (3-10 turns)

**Key Functions:**
- `simulate_consequences()` - Forward projection
- `estimate_recovery_time()` - Time to recover from failure
- `assess_downside_risk()` - Worst-case scenario

---

#### `outcome_feedback_loop.py`
**Purpose:** Connect outcomes to minister/KIS recalibration

**Key Functions:**
- `process_outcome()` - Analyze success/failure
- `generate_feedback_signals()` - Adjustment signals
- `update_minister_weights()` - Adjust minister influence

---

#### `failure_analysis.py`
**Purpose:** Root cause diagnosis for failures

**Key Functions:**
- `analyze_failure()` - Root cause analysis
- `assign_blame()` - Which minister/system failed?
- `generate_recommendations()` - How to improve

---

### Submodule: `persona/validation/`

#### `mode_validator.py`
**Purpose:** Enforce mode consistency

**Key Functions:**
- `validate_mode_response()` - Check response matches mode
- `detect_mode_drift()` - Catch accidental mode switching
- `correct_mode_violation()` - Fix mode inconsistencies

**Validates:**
- QUICK: Personal & direct (no council references)
- WAR: Victory-focused language
- MEETING: Multi-perspective synthesis
- DARBAR: Full council involvement

---

#### `identity_validator.py`
**Purpose:** Prevent Persona self-contradiction

**Key Functions:**
- `check_contradiction()` - Detect logical inconsistencies
- `track_doctrine_alignment()` - Verify persona consistency
- `enforce_red_lines()` - Protect fundamentals

---

#### `contradiction_detector.py`
**Purpose:** Detect contradictory statements

**Key Functions:**
- `detect_self_contradiction()` - Compare with past statements
- `log_contradiction()` - Record for audit trail
- `force_acknowledgment()` - Require contradiction acknowledgment

---

### Submodule: `persona/persistence/`

#### `conversation_arc.py`
**Purpose:** Long-term narrative tracking

**Key Functions:**
- `track_arc()` - Maintain story coherence
- `detect_loops()` - Catch circular conversations
- `summarize_arc()` - Generate narrative summary

---

#### `memory_store.py`
**Purpose:** Low-level memory storage operations

**Key Functions:**
- `save_episode()` - Write to JSONL
- `load_episodes()` - Read from JSONL
- `archive_old()` - Compress old episodes

---

### Submodule: `persona/pwm_integration/`

#### `pwm_bridge.py` ⭐
**Purpose:** Sync episodic/metrics → PWM (Personal World Model)

**Key Functions:**
- `record_observation()` - Log observation for PWM
- `periodic_pwm_sync()` - Every 100-turn validation
- `generate_actionable_insights()` - PWM-based insights

**Update Rule:**
- Episodic/Metrics: Every turn (fast)
- PWM: Every 100 turns (after validation, high-confidence only)

---

## Module: `ml/` (ML Learning System)

### Core Files

#### `sovereign_orchestrator.py` ⭐
**Purpose:** 12-system integration hub

**Key Functions:**
- `initialize_synthetic_human()` - Attach human simulator
- `run_turn()` - Full orchestration for one turn
- `get_state_snapshot()` - Current system state

**Returns Per Turn:**
- `next_input` - Next human input
- `outcome` - Success/failure
- `metrics` - Rolling 100-turn metrics
- `alerts` - Validation alerts
- `failure_report` - Root causes (if failure)

**Lines:** 600+

---

#### `ml_orchestrator.py`
**Purpose:** ML wisdom pipeline orchestrator

**Key Functions:**
- `process_decision()` - Full ML pipeline
- `record_outcome()` - Store outcome for training
- `save_session()` - Save ML session state

---

#### `system_retraining.py`
**Purpose:** Systematic retraining every 200 turns

**Key Functions:**
- `extract_success_patterns()` - Find what works
- `update_ministers()` - Retrain per domain
- `evolve_doctrine()` - Update doctrines from patterns
- `rebalance_kis_weights()` - Adjust KIS weights

---

#### `minister_retraining.py`
**Purpose:** Per-minister retraining logic

**Key Functions:**
- `retrain_minister()` - Update specific minister
- `update_confidence_formulas()` - Adjust confidence calculations
- `apply_learned_doctrine()` - Incorporate new learnings

---

#### `pattern_extraction.py` ⭐
**Purpose:** Identify failure clusters and patterns

**Key Functions:**
- `extract_patterns()` - Find recurring patterns
- `detect_failure_clusters()` - Sequential failures
- `identify_regret_clusters()` - High-regret decisions
- `generate_learning_signals()` - Actionable improvements

**Patterns Detected:**
- `long_failure_streak` - 3+ consecutive failures
- `high_regret_cluster` - Multiple high-regret decisions
- `weak_domain_pattern` - Domain consistently underperforming

---

#### `vector_memory.py`
**Purpose:** Vector-based memory for semantic search

**Key Functions:**
- `embed_episode()` - Create vector embedding
- `search_similar()` - Semantic similarity search
- `build_index()` - Create/update vector index

**Backend:** FAISS (cpu)

---

#### `reward_shaping.py`
**Purpose:** Outcome-based reward signals

**Key Functions:**
- `compute_reward()` - Calculate reward from outcome
- `shape_reward()` - Adjust for difficulty
- `apply_to_ministers()` - Distribute reward signal

---

#### `doctrine_update.py`
**Purpose:** Doctrine evolution from patterns

**Key Functions:**
- `update_doctrine_from_patterns()` - Incorporate learnings
- `validate_doctrine_change()` - Ensure consistency
- `commit_doctrine_update()` - Save updated doctrine

---

### Submodule: `ml/kis/` (Knowledge Integration System)

#### `knowledge_integration_system.py` ⭐
**Purpose:** Multi-factor knowledge ranking

**Key Classes:**
- `KnowledgeIntegrationSystem` - Main KIS engine
- `KISRequest` - Request object
- `KISResult` - Result with knowledge + trace

**Key Functions:**
- `synthesize_knowledge()` - Rank and return top-N
- `compute_domain_weight()` - Domain confidence weighting
- `compute_type_weight()` - Knowledge type weighting
- `compute_memory_weight()` - Reinforcement/penalty weighting
- `compute_context_weight()` - Keyword matching
- `compute_goal_weight()` - Strategic language detection

**Weight Formula:**
```
KIS = domain × type × memory × context × goal
```

**Lines:** 400+

---

### Submodule: `ml/features/`

#### `feature_extractor.py` ⭐
**Purpose:** Convert situations to feature vectors

**Key Functions:**
- `build_feature_vector()` - Create 41-dim vector

**Feature Categories:**
- Situation features (14): decision_type, risk_level, time_horizon, etc.
- Constraint features (6): irreversibility, fragility, optionality_loss
- Knowledge features (14): used_principle, avg_kis_[type], etc.
- Action features (7): action_type, reversibility, resource_cost

**Total:** ~41 features

---

### Submodule: `ml/labels/`

#### `label_generator.py` ⭐
**Purpose:** Convert outcomes to training labels

**Key Functions:**
- `generate_type_weights()` - Adjust knowledge type weights

**Logic:**
```
If failure + irreversibility:
  ↑ warning_weight, principle_weight

If failure + rule-heavy:
  ↓ rule_weight

If success + irreversible:
  ↑ principle_weight

If advice + high regret:
  ↓ advice_weight
```

**Bounds:** All weights clamped [0.7, 1.3]

---

### Submodule: `ml/judgment/`

#### `ml_judgment_prior.py` ⭐
**Purpose:** Learn which knowledge types succeed in similar situations

**Key Classes:**
- `MLJudgmentPrior` - Main model

**Key Functions:**
- `add_training_sample()` - Add (features, label) pair
- `train()` - Batch train every 50 samples
- `predict_prior()` - Get priors for new situation
- `save()` / `load()` - Model persistence

**Learning Algorithm:**
1. Accumulate training samples
2. Group by situation_hash (decision_type + risk_level + irreversibility)
3. Compute average learned weights per group
4. Store as priors

**Application:**
```
adjusted_KIS = KIS × ml_prior_weight
(only if model confidence > 0.6)
```

---

### Submodule: `ml/llm_handshakes/`

#### `llm_interface.py` ⭐
**Purpose:** Safe LLM calls for sensing (not deciding)

**Key Functions:**
- `run_handshake_sequence()` - 4-call sensing pipeline

**4 Calls (Collapsed to 2):**
1. **Situation + Constraints:** decision_type, risk_level, irreversibility_score
2. **Counterfactual Sketch:** 3 options with downsides/upsides
3. **Intent Detection:** goal_orientation, emotional_pressure

**Safety Rules:**
- LLM output never shown directly
- All numeric fields clamped
- Confidence gates everything
- Rules override LLM always
- LLM never sees ML weights

---

### Submodule: `ml/models/`

| File | Purpose |
|------|---------|
| `judgment_prior.json` | Trained ML judgment prior model |

---

### Submodule: `ml/cache/`

| File | Purpose |
|------|---------|
| `session.json` | Session cache (decision log, temporary state) |

---

## Module: `hse/` (Human Simulation Environment)

### Core Files

#### `human_profile.py` ⭐
**Purpose:** Define synthetic human personality

**Key Classes:**
- `SyntheticHuman` - Human simulator

**Attributes:**
- Age, personality traits
- Risk tolerance
- Goals and motivations
- Background story

---

#### `personality_drift.py`
**Purpose:** Personality evolution over time

**Key Functions:**
- `update_personality()` - Adjust based on experiences
- `apply_stress_effects()` - Stress-induced changes
- `track_drift()` - Monitor personality changes

---

#### `crisis_injector.py`
**Purpose:** Inject crisis scenarios for stress testing

**Key Functions:**
- `inject_crisis()` - Trigger crisis event
- `generate_crisis_chain()` - Compounding crises
- `measure_response_quality()` - Evaluate persona response

**Crisis Types:**
- Job loss
- Health emergency
- Relationship breakdown
- Financial crisis

---

#### `population_manager.py`
**Purpose:** Manage multiple synthetic humans

**Key Functions:**
- `add_human()` - Add to population
- `select_human()` - Choose for interaction
- `track_population_stats()` - Aggregate statistics

---

#### `analytics_server.py`
**Purpose:** Flask API for analytics

**Endpoints:**
- `/metrics` - Current metrics
- `/episodes` - Recent episodes
- `/dashboard` - Dashboard data

**Port:** Configurable (default 5000)

---

### Submodule: `hse/simulation/`

#### `synthetic_human_sim.py` ⭐
**Purpose:** Main synthetic human simulation engine

**Key Functions:**
- `generate_input()` - Generate realistic human input
- `react_to_response()` - React to persona response
- `run_conversation()` - Full conversation loop

**LLM Used:** `llama3.1:8b-instruct-q4_0`

**Timeout:** 30 seconds with fallback

---

#### `human_persona_adapter.py`
**Purpose:** Bridge between human and persona

**Key Functions:**
- `adapt_human_input()` - Format for persona
- `adapt_persona_response()` - Format for human
- `track_trust()` - Measure trust trajectory

---

#### `stress_orchestrator.py`
**Purpose:** Orchestrate stress testing scenarios

**Key Functions:**
- `start_stress_scenario()` - Begin stress test
- `escalate_stress()` - Increase pressure
- `measure_coherence()` - Check persona coherence

---

#### `bidirectional_simulation.py`
**Purpose:** Two-way conversation simulation

**Key Functions:**
- `run_bidirectional()` - Full two-way loop
- `track_conversation_quality()` - Quality metrics
- `detect_conversation_loops()` - Catch circular patterns

---

## Module: `sovereign/` (Sovereign Runtime)

### Core Files

#### `llm_adapter.py`
**Purpose:** LLM adapter for sovereign system

**Key Functions:**
- `generate()` - Unified LLM interface
- `check_health()` - LLM health check

---

#### `prime_confident.py`
**Purpose:** Final decision approval/rejection

**Key Functions:**
- `review_recommendation()` - Approve/reject council rec
- `override_if_needed()` - Override in edge cases
- `ensure_doctrine_alignment()` - Check doctrine consistency

---

### Submodule: `sovereign/council/`

(Similar to `persona/council/` but for sovereign runtime)

---

### Submodule: `sovereign/ministers/`

(Similar to `persona/ministers.py` but for sovereign runtime)

---

## Module: `data/` (Knowledge Bases)

### Structure

```
data/
├── ministers/
│   ├── career_risk/
│   │   ├── principles.json
│   │   ├── rules.json
│   │   ├── warnings.json
│   │   ├── claims.json
│   │   └── advice.json
│   ├── optionality_guide/
│   │   └── ...
│   └── [other_domains]/
└── doctrines/
    └── [minister_doctrines]
```

### Knowledge Entry Format

```json
{
  "aku_id": "opt-001",
  "content": "Preserve optionality in irreversible decisions",
  "type": "principle",
  "source": {
    "book": "The Optionality Handbook",
    "chapter": 3
  },
  "memory": {
    "reinforcement_count": 5,
    "penalty_count": 0,
    "last_used": "2026-02-15"
  }
}
```

---

## Module: `Memory/` (Episodic Memory Storage)

### Structure

```
Memory/
├── YYYY-MM-DD_episodes.jsonl
├── metrics_snapshot.json
└── patterns.json
```

### Episode Format (JSONL)

```json
{"turn": 150, "domain": "career", "user_input": "...", "recommendation": "...", "confidence": 0.75, "outcome": "failure", "regret": 0.8}
{"turn": 151, "domain": "finance", ...}
```

---

## Module: `analytics/` (Dashboard & Reporting)

### Files

| File | Purpose |
|------|---------|
| `dashboard.py` | Real-time performance dashboard |

**Dashboard Shows:**
- Success rate (rolling 100 turns)
- Weak domains (<50% success)
- Mode stability
- Contradiction count
- Memory size
- Improvement trajectory

---

## Module: `tests/` (Test Suite)

### Structure

```
tests/
├── test_ml_wisdom.py        # ML system tests
├── test_mode_orchestrator.py # Mode system tests
├── test_council.py          # Council tests
├── test_memory.py           # Memory tests
└── test_integration.py      # End-to-end tests
```

---

## Module: `utils/` (Utilities)

### Common Utilities

| File | Purpose |
|------|---------|
| `json_utils.py` | JSON helpers |
| `file_utils.py` | File operations |
| `time_utils.py` | Time formatting |
| `logging_utils.py` | Logging setup |

---

## Module: `scripts/` (Helper Scripts)

### Scripts

| Script | Purpose |
|--------|---------|
| `run_benchmark.py` | Run performance benchmarks |
| `export_memory.py` | Export memory for analysis |
| `visualize_metrics.py` | Generate metric visualizations |
| `cleanup_logs.py` | Log cleanup |

---

## Module: `integrations/` (External Integrations)

### Integrations

| File | Purpose |
|------|---------|
| `ollama_integration.py` | Ollama API integration |
| `vector_db_integration.py` | Vector database (FAISS) |
| `flask_api.py` | Flask API endpoints |

---

## Module: `ingestion/` (Knowledge Ingestion)

### Purpose
Ingest knowledge from external sources (PDFs, documents, etc.)

### Files

| File | Purpose |
|------|---------|
| `pdf_ingestor.py` | PDF extraction |
| `knowledge_parser.py` | Parse knowledge entries |
| `validation.py` | Validate ingested knowledge |

---

## Module: `llm/` (LLM Utilities)

### Files

| File | Purpose |
|------|---------|
| `model_manager.py` | LLM model management |
| `prompt_templates.py` | Prompt templates |
| `response_parser.py` | Parse LLM responses |

---

## Module: `rag_cache/` & `rag_storage/` (RAG)

### Purpose
Retrieval-Augmented Generation caching and storage

### Files

| File | Purpose |
|------|---------|
| `cache_manager.py` | RAG cache management |
| `storage.py` | RAG storage backend |
| `retriever.py` | Knowledge retrieval |

---

## Module: `multi_agent_sim/` (Multi-Agent Simulation)

### Purpose
Simulate multiple agents interacting

### Files

| File | Purpose |
|------|---------|
| `agent.py` | Agent definition |
| `simulation.py` | Multi-agent simulation loop |
| `metrics.py` | Multi-agent metrics |

---

## Summary by Priority

### ⭐ Critical Files (Must Know)
1. `persona/main.py` - Entry point
2. `persona/modes/mode_orchestrator.py` - 4-mode routing
3. `persona/council/dynamic_council.py` - Minister selection
4. `persona/ministers.py` - 18 ministers
5. `persona/learning/episodic_memory.py` - Memory storage
6. `persona/learning/performance_metrics.py` - Metrics tracking
7. `ml/sovereign_orchestrator.py` - 12-system integration
8. `ml/kis/knowledge_integration_system.py` - KIS ranking
9. `ml/features/feature_extractor.py` - Feature extraction
10. `ml/judgment/ml_judgment_prior.py` - ML learning
11. `hse/simulation/synthetic_human_sim.py` - Synthetic human
12. `persona/pwm_integration/pwm_bridge.py` - PWM sync

### 📚 Key Documentation
1. `SYSTEM_STATUS.md` - System verification
2. `MODE_SELECTION_GUIDE.md` - Mode usage
3. `HYBRID_MEMORY_ARCHITECTURE.md` - Memory design
4. `SOVEREIGN_ORCHESTRATOR_GUIDE.md` - 12-system guide
5. `documentation/README.md` - This documentation index

---

📄 **Next:** [`04_DATA_FLOW.md`](./04_DATA_FLOW.md) - How data moves through the system
