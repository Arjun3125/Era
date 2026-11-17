# ERA Architecture Map

> **Generated from source code** — every reference points to an actual file, class, or function.

---

## 1. System Identity

**ERA** (Executive Reasoning Architecture) is a modular decision-intelligence
pipeline that simulates a "council of ministers" deliberating on user queries.
A final sovereign authority — **PrimeConfident** — applies doctrine-based
constraints before emitting a decision.

The system is designed for:
- Personal decision support with multi-perspective analysis
- Simulation-based policy evaluation via reinforcement-learning environments
- Self-improvement through episodic memory, pattern extraction, and calibration

---

## 2. High-Level Data Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  DecisionPipelineEngine  (modules/decision_pipeline) │
│  ═══════════════════════════════════════════════════  │
│                                                       │
│  Stage 1 ► Input Normalization                        │
│  Stage 2 ► Runtime Config Loading                     │
│  Stage 3 ► Domain Analysis                            │
│  Stage 4 ► Mode Routing  ─────────┐                  │
│  Stage 5 ► Knowledge Synthesis    │                  │
│  Stage 6 ► Council Execution ◄────┘ (mode-selected   │
│  Stage 7 ► Council Normalization     ministers)       │
│  Stage 8 ► Prime Decision                             │
│  Stage 9 ► Decision Packaging                         │
│  Stage 10 ► Contract Validation                       │
│                                                       │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
              DecisionEnvelope
       (final_decision, telemetry, errors)
```

---

## 3. Directory Layout

```
era/
├── config/
│   └── settings.py              # RuntimeSettings: env-var loading, normalization
├── core/
│   ├── contracts/
│   │   ├── __init__.py          # Re-exports all typed contracts
│   │   ├── io.py                # InputContract, DecisionContract, ErrorContract, …
│   │   ├── context.py           # ExecutionContext: mutable state bag for runs
│   │   ├── events.py            # EventType, EventLevel, EventRecord
│   │   └── module.py            # ModulePlugin protocol, ModuleResult, ModuleStatus
│   └── orchestrator/
│       └── runtime.py           # PipelineOrchestrator: stage registration & execution
├── decision_env/
│   ├── environment.py           # DecisionEnvironment, MultiStep, LongHorizon
│   ├── episode_runner.py        # EpisodeRunner, EraDecisionAgent, PolicyEvaluation
│   ├── scenario_generator.py    # ScenarioGenerator, DecisionScenario
│   ├── simulator.py             # OutcomeSimulator
│   ├── reward_function.py       # RewardFunction, RewardBreakdown
│   ├── reward_model.py          # RewardModel, shaped_reward, delayed_reward
│   ├── state_model.py           # DecisionState, LongHorizonState, StateTransition
│   └── transition_model.py      # TransitionModel, LongHorizonTransitionModel
├── modules/
│   ├── decision_pipeline/       # DecisionPipelineEngine (stage orchestration)
│   ├── input_normalization/     # InputNormalizationModule
│   ├── runtime_config/          # RuntimeConfigModule
│   ├── domain_analysis/         # DomainAnalysisModule
│   ├── council_router/          # ModeRoutingModule, ModeOrchestrator, ModeStrategy
│   ├── knowledge_synthesis/     # KnowledgeSynthesisModule
│   ├── council_execution/       # CouncilExecutionEngine, NativeCouncil, _NativeMinister
│   ├── council_normalization/   # CouncilNormalizationModule
│   ├── prime_decision/          # PrimeDecisionEngine, NativePrimeDecider
│   ├── decision_packaging/      # DecisionPackagingModule
│   ├── contract_validation/     # ContractValidationModule
│   ├── uncertainty/             # TemperatureCalibrator, RiskModel, ECE, Brier
│   ├── calibration/             # Advanced calibration utilities
│   ├── expert_router/           # ExpertRouterPredictor
│   ├── moe_router/              # MoERouterPredictor (Mixture of Experts)
│   ├── council_learning/        # CouncilWeightPredictor
│   ├── reasoning_controller/    # ReasoningControllerPredictor
│   ├── mode_controller/         # ModeControllerPredictor
│   ├── minister_policies/       # Learned minister policy models
│   ├── rl/                      # Reinforcement learning integration
│   ├── policy_model/            # Policy network wrappers
│   ├── value_model/             # Value function models
│   ├── representation/          # State embedding / representation layers
│   ├── decision_engine/         # Standalone decision engine
│   ├── decision_simulator/      # Simulation utilities
│   ├── evaluation_engine/       # Eval harness for pipeline quality
│   ├── failure_analysis/        # Failure detection & classification
│   ├── learning_core/           # Core learning loop infrastructure
│   └── scenario_memory/         # Memory-backed scenario retrieval
├── persona/
│   ├── main.py                  # Interactive loop, mode selection, MCA integration
│   ├── brain.py                 # PersonaBrain: HALT decision logic
│   ├── state.py                 # CognitiveState: turn-level mutable state
│   ├── context.py               # build_system_context, trim_response
│   ├── analysis.py              # Situation, domain, emotional, coherence assessment
│   ├── knowledge_engine.py      # KIS (Knowledge Integration & Synthesis)
│   ├── council.py               # CouncilAggregator, CouncilRecommendation
│   ├── doctrine_loader.py       # DoctrineLoader: YAML doctrine parsing
│   ├── clarify.py               # Clarifying question generation
│   ├── learning/                # EpisodicMemory, PerformanceMetrics, OutcomeFeedbackLoop
│   ├── validation/              # IdentityValidator
│   ├── modes/                   # Legacy ModeOrchestrator, ModeMetrics
│   └── council/                 # DynamicCouncil (mode-aware council wrapper)
├── sovereign/
│   └── prime_confident.py       # PrimeConfident: doctrine-driven final authority
├── hse/
│   └── simulation/              # SyntheticHumanSimulation
├── ml/
│   └── pattern_extraction.py    # PatternExtractor
├── system_main.py               # Compatibility entrypoint → run_refactored.py
└── run_refactored.py            # Primary runtime: pipeline init, training loops
```

---

## 4. Entrypoints

| Entrypoint | File | Purpose |
|---|---|---|
| **Interactive CLI** | `persona/main.py → main()` | Mode selection, user loop, MCA decision per turn |
| **Compatibility shim** | `system_main.py` | Delegates to `run_refactored.py` |
| **Refactored runtime** | `run_refactored.py` | `DecisionPipelineEngine.create()`, training loops |

---

## 5. Layer Architecture

### Layer 1 — Contracts (`core/contracts/`)

Typed `@dataclass` definitions with strict normalization in `__post_init__`.
Every field is validated, clamped, or coerced to a canonical form.

| Contract | Fields | Purpose |
|---|---|---|
| `InputContract` | `user_input`, `session_id`, `metadata` | Pipeline entry |
| `DecisionContract` | `decision`, `confidence`, `rationale`, `mode`, `metadata` | Pipeline exit |
| `ErrorContract` | `code`, `message`, `stage`, `recoverable`, `details` | Error tracking |
| `ModeResolutionContract` | `mode`, `should_invoke_council`, `selected_ministers`, `rationale`, `confidence` | Mode routing output |
| `DomainAnalysisContract` | `domains`, `confidence`, `source` | Domain detection output |
| `KnowledgeContract` | `synthesized_knowledge`, `sources`, `metadata` | Knowledge layer output |
| `CouncilContract` | `outcome`, `recommendation`, `consensus_strength`, `minister_positions`, … | Council deliberation output |
| `CouncilNormalizationContract` | Normalized council payload | Post-council normalization |
| `DecisionPackagingContract` | Packaged decision envelope | Final packaging |
| `ContractValidationContract` | Validation results | Schema compliance check |
| `PipelineTelemetryContract` | `stage_timings_ms`, `total_runtime_ms`, … | Performance metrics |
| `PipelineErrorSummaryContract` | Aggregated errors | Error roll-up |
| `RuntimeConfigContract` | Loaded config snapshot | Config state capture |
| `RequestContextContract` | Request-level metadata | Context enrichment |

### Layer 2 — Orchestration (`core/orchestrator/runtime.py`)

`PipelineOrchestrator` provides:
- **Stage registration** with named handlers and error policies (`abort` / `degrade`)
- **Sequential execution** with per-stage timing
- **Error accumulation** via `ErrorContract`
- **Event emission** via `EventRecord` (`RUN_STARTED`, `STAGE_COMPLETED`, etc.)
- **Strict mode** toggle for zero-tolerance error handling
- **Result**: `OrchestrationResult(run_id, status, context, stage_timings_ms, total_runtime_ms)`

### Layer 3 — Modules (`modules/`)

Each module implements the `ModulePlugin` protocol:
```python
class ModulePlugin(Protocol):
    def name(self) -> str: ...
    def capabilities(self) -> Mapping[str, Any]: ...
    def validate(self, context: ExecutionContext) -> None: ...
    def execute(self, context: ExecutionContext) -> ModuleResult: ...
    def health(self) -> ModuleHealth: ...
```

### Layer 4 — Persona (`persona/`)

The human-facing interactive layer. `persona/main.py` orchestrates:
1. LLM runtime initialization (OllamaRuntime / OllamaAdapter)
2. Mode selection (Quick/War/Meeting/Darbar)
3. Per-turn: situation assessment → LLM response → MCA decision → background analysis
4. Learning systems: episodic memory, performance metrics, pattern extraction

### Layer 5 — Sovereign (`sovereign/`)

`PrimeConfident` is the final decision authority:
- Loads doctrine from YAML via `DoctrineLoader`
- Checks doctrine constraints (anti-moralization)
- Detects emotional distortion (high confidence + low consensus)
- Detects pattern recurrence (excessive rationalizations)
- Falls through to standard council evaluation

---

## 6. Cross-Cutting Concerns

| Concern | Implementation |
|---|---|
| **Observability** | `EventRecord` emission at every stage boundary |
| **Error resilience** | `ErrorPolicy.DEGRADE` allows pipeline continuation |
| **Type safety** | `__post_init__` validation on all contracts |
| **Normalization** | Every text/numeric/boolean input is canonicalized |
| **Extensibility** | `ModulePlugin` protocol for plug-and-play stages |
| **Simulation** | `DecisionEnvironment` family for RL training |
| **Uncertainty** | Composite U score, temperature calibration, ECE/Brier metrics |
