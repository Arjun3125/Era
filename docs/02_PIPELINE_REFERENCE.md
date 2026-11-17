# ERA Pipeline Reference

> **Source of truth**: `modules/decision_pipeline/engine.py` — `DecisionPipelineEngine`

---

## 1. Pipeline Overview

The ERA decision pipeline is a **10-stage sequential processor** that transforms
a raw user input into a validated, packaged decision envelope. Each stage is a
`ModulePlugin` registered with a `PipelineOrchestrator`.

```
Input ──► [1] Input Normalization
          [2] Runtime Config
          [3] Domain Analysis
          [4] Mode Routing
          [5] Knowledge Synthesis
          [6] Council Execution
          [7] Council Normalization
          [8] Prime Decision
          [9] Decision Packaging
          [10] Contract Validation ──► DecisionEnvelope
```

---

## 2. Stage-by-Stage Reference

### Stage 1 — Input Normalization

| Key | Value |
|---|---|
| **Module** | `InputNormalizationModule` |
| **Location** | `modules/input_normalization/` |
| **Input** | Raw `user_input` string, `session_id`, `metadata` |
| **Output** | `InputContract` (validated, trimmed, session-assigned) |
| **Error Policy** | `abort` |

**Behavior**: Strips whitespace, validates non-empty input, assigns session ID
via UUID if missing, normalizes metadata mapping.

---

### Stage 2 — Runtime Config

| Key | Value |
|---|---|
| **Module** | `RuntimeConfigModule` |
| **Location** | `modules/runtime_config/` |
| **Input** | `ExecutionContext.config` |
| **Output** | `RuntimeConfigContract` (loaded settings snapshot) |
| **Error Policy** | `degrade` |

**Behavior**: Loads `config/settings.py` → `RuntimeSettings`. Supports env-var
overrides. Falls back to defaults if loading fails.

**Key Config Values** (from `config/settings.py`):

| Setting | Type | Default | Source |
|---|---|---|---|
| `orchestrator_strict` | `bool` | `False` | `ERA_ORCHESTRATOR_STRICT` |
| `decision_pipeline_enabled` | `bool` | `True` | `ERA_DECISION_PIPELINE_ENABLED` |
| `reasoning_controller_enabled` | `bool` | `False` | `ERA_REASONING_CONTROLLER_ENABLED` |
| `expert_router_enabled` | `bool` | `False` | `ERA_EXPERT_ROUTER_ENABLED` |
| `moe_router_enabled` | `bool` | `False` | `ERA_MOE_ROUTER_ENABLED` |
| `council_weight_model_enabled` | `bool` | `False` | `ERA_COUNCIL_WEIGHT_MODEL_ENABLED` |
| `mode_controller_enabled` | `bool` | `False` | `ERA_MODE_CONTROLLER_ENABLED` |
| `risk_threshold` | `float` | `0.7` | `ERA_RISK_THRESHOLD` |

---

### Stage 3 — Domain Analysis

| Key | Value |
|---|---|
| **Module** | `DomainAnalysisModule` |
| **Location** | `modules/domain_analysis/` |
| **Input** | `InputContract.user_input` |
| **Output** | `DomainAnalysisContract` (`domains: List[str]`, `confidence: float`) |
| **Error Policy** | `degrade` |

**Behavior**: Classifies user input into domain categories (career, financial,
relationships, health, strategy, power, ethics, innovation). Uses keyword
detection and/or LLM-backed classification.

---

### Stage 4 — Mode Routing

| Key | Value |
|---|---|
| **Module** | `ModeRoutingModule` |
| **Location** | `modules/council_router/module.py` |
| **Input** | Requested mode, routing context, user input |
| **Output** | `resolved_mode`, `should_invoke_council`, `selected_ministers`, `execution_plan`, `mode_contract` |
| **Error Policy** | `degrade` |

**Behavior**:
1. Merges routing context from `config`, `input.metadata`, `run.metadata`, `state`
2. Applies **ModeControllerPredictor** (if enabled) — learned budget prediction
3. Applies **ReasoningControllerPredictor** (if enabled) — budget overrides
4. Resolves mode via `ModeRoutingEngine` → `ModeOrchestrator`
5. Optionally applies **expert weight models** in priority order:
   - `CouncilWeightPredictor` → `MoERouterPredictor` → `ExpertRouterPredictor`

**Valid Modes** (from `_VALID_MODES`):

| Mode | Council? | Ministers | Frame |
|---|---|---|---|
| `baseline` | No | 0 | Direct output, bypass all ML/KIS/PWM/memory |
| `quick` | No | 0 | 1:1 mentoring, personal, fast |
| `meeting` | Yes | 3–5 | Structured debate, balanced synthesis |
| `war` | Yes | 5 | Victory-focused: Risk, Power, Strategy, Technology, Timing |
| `darbar` | Yes | 18 | Full council deliberation |

**Mode Aliases** (from `_MODE_ALIASES`):

| Alias | Resolves To |
|---|---|
| `quick_mode`, `fast` | `quick` |
| `normal`, `standard`, `default` | `meeting` |
| `war_mode` | `war` |
| `full_council`, `board` | `darbar` |

**Execution Plan Flags** (from `_execution_plan_defaults()`):

| Flag | Default | Baseline Override |
|---|---|---|
| `use_dynamic_council` | `False` | `False` |
| `use_ml_prior` | `False` | `False` |
| `use_kis` | `False` | `False` |
| `use_pwm` | `False` | `False` |
| `use_memory` | `True` | `False` |

---

### Stage 5 — Knowledge Synthesis

| Key | Value |
|---|---|
| **Module** | `KnowledgeSynthesisModule` |
| **Location** | `modules/knowledge_synthesis/` |
| **Input** | `user_input`, active `domains`, `domain_confidence` |
| **Output** | `KnowledgeContract` (synthesized knowledge items, sources) |
| **Error Policy** | `degrade` |

**Behavior**: Performs KIS (Knowledge Integration & Synthesis) — retrieves
domain-specific knowledge and synthesizes actionable intelligence for the
council to consume.

---

### Stage 6 — Council Execution

| Key | Value |
|---|---|
| **Module** | `CouncilExecutionEngine` (via `CouncilExecutionModule`) |
| **Location** | `modules/council_execution/engine.py` |
| **Input** | `user_input`, `selected_ministers`, `mode`, `routing_context` |
| **Output** | `CouncilContract` (outcome, recommendation, minister positions, consensus) |
| **Error Policy** | `degrade` |

**Behavior**: See [03_MINISTER_REGISTRY.md](03_MINISTER_REGISTRY.md) for full
minister details. Key flow:
1. Select ministers per mode strategy
2. Each minister runs `analyze(user_input, context)` → stance/confidence/reasoning
3. Aggregate positions into consensus
4. Determine recommendation (support/oppose/defer)
5. Check red-line triggers

---

### Stage 7 — Council Normalization

| Key | Value |
|---|---|
| **Module** | `CouncilNormalizationModule` |
| **Location** | `modules/council_normalization/` |
| **Input** | Raw council output |
| **Output** | `CouncilNormalizationContract` (canonical council payload) |
| **Error Policy** | `degrade` |

**Behavior**: Normalizes council output keys, clamps confidence values to
[0.0, 1.0], deduplicates warnings, normalizes stances to the canonical set
(`support`, `oppose`, `neutral`).

---

### Stage 8 — Prime Decision

| Key | Value |
|---|---|
| **Module** | `PrimeDecisionEngine` |
| **Location** | `modules/prime_decision/engine.py` |
| **Input** | Normalized council recommendation, minister outputs, mode |
| **Output** | `PrimeDecisionResult` (final_decision, decision_contract, warnings) |
| **Error Policy** | `abort` |

**Behavior**:
1. Normalize council recommendation (map to canonical outcomes/recommendations)
2. Normalize minister outputs (stance/confidence/reasoning/red_line)
3. Check bypass conditions (quick mode, baseline, ablation, no-council)
4. Delegate to `NativePrimeDecider.decide()` or legacy `PrimeConfident.decide()`
5. Derive confidence from LLM assessment, final decision, or council average
6. Build `DecisionContract`

**Final Outcome Values**: `accept`, `accept_with_mitigation`, `defer`, `reject`, `direct_response`

**Recommendation Mapping** (from `_map_recommendation()`):

| Source Token | Maps To |
|---|---|
| `strong_consensus_support`, `aggressive_proceed`, `accept`, `accept_with_mitigation` | `support` |
| `strong_consensus_oppose`, `red_line_blocks_recommendation`, `reject` | `oppose` |
| `deep_disagreement_defer_decision`, `insufficient_data`, `no_council_response` | `defer` |

---

### Stage 9 — Decision Packaging

| Key | Value |
|---|---|
| **Module** | `DecisionPackagingModule` |
| **Location** | `modules/decision_packaging/` |
| **Input** | All accumulated context and decision |
| **Output** | `DecisionPackagingContract` (final envelope) |
| **Error Policy** | `degrade` |

**Behavior**: Assembles the `DecisionEnvelope` with:
- `final_decision`: The prime decision payload
- `council_result`: Council deliberation output
- `mode_resolution`: Mode routing metadata
- `telemetry`: Stage timings and performance metrics
- `errors`: Aggregated pipeline errors

---

### Stage 10 — Contract Validation

| Key | Value |
|---|---|
| **Module** | `ContractValidationModule` |
| **Location** | `modules/contract_validation/` |
| **Input** | Complete pipeline context |
| **Output** | `ContractValidationContract` (validation results) |
| **Error Policy** | `degrade` |

**Behavior**: Validates all emitted contracts against their schema
constraints. Reports violations as warnings rather than hard failures.

---

## 3. Error Handling

The `PipelineOrchestrator` supports two error policies per stage:

| Policy | Behavior |
|---|---|
| `ErrorPolicy.ABORT` | Pipeline halts immediately. `RunStatus.ABORTED` |
| `ErrorPolicy.DEGRADE` | Error recorded, pipeline continues. `RunStatus.COMPLETED_WITH_ERRORS` |

When `strict=True`, even `DEGRADE`-policy stages cause abort on error.

---

## 4. Telemetry

Every stage emits `EventRecord` objects:
- `STAGE_STARTED` — before handler invocation
- `STAGE_COMPLETED` / `STAGE_FAILED` / `STAGE_DEGRADED` — after handler
- `RUN_STARTED` / `RUN_COMPLETED` / `RUN_ABORTED` — pipeline boundaries

Each record includes: `run_id`, `event_type`, `payload`, `stage`, `level`, `timestamp`.

---

## 5. Pipeline Creation

```python
# From run_refactored.py / persona/main.py
pipeline = DecisionPipelineEngine.create(
    llm=llm,
    prime_decider=prime,
    risk_threshold=0.7,
)

result = pipeline.run(
    user_input="Should I take this job offer?",
    requested_mode="meeting",
    routing_context={"domains": ["career"]},
    metadata={"source": "interactive"},
)
```
