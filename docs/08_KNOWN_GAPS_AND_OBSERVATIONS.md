# ERA Pipeline: Known Gaps & Implementation Observations

> **Source**: Based on recursive codebase analysis against the requested architecture constraints.

---

## 1. Objective Status
The codebase structure clearly reflects an evolution towards a robust, strict-contract orchestration pipeline (`DecisionPipelineEngine`). However, certain components remain mocked or partially implemented, likely awaiting model integration or RL feedback loops.

---

## 2. Identified Implementation Gaps

### 1. ML Predictors are Stubbed
The `modules/council_router/module.py` defines integration points for several advanced machine-learning routing models, but the implementations are placeholders.
- `ReasoningControllerPredictor`
- `MoERouterPredictor`
- `CouncilWeightPredictor`
- `ModeControllerPredictor`

*Observation*: The config supports enabling these via `ERA_*_ENABLED` flags, but if enabled, they will likely return default/fallback predictions rather than active neural network inferences.

### 2. Knowledge Integration & Synthesis (KIS) Module
The `KnowledgeSynthesisModule` is defined as Stage 5 in the pipeline. It is backed by `persona/knowledge_engine.py`, which queries the Chroma vector store (`chroma_knowledge/`, collection `era_minister_knowledge`) over the assembled minister knowledge corpus (49,060+ chunks), then falls back to file-based 5-factor KIS scoring.
- *Observation*: Domain knowledge is loaded from `data/ministers/{domain}/{category}.json`; generated topic stores and the Chroma index are build artifacts and are not tracked in git.

### 3. Native Council Uses LLM Ministers in Meeting/Darbar
The `NativeCouncil` (`modules/council_execution/engine.py`) uses hardcoded keyword scoring (`urgency`, `risk_score`, `uncertainty`) for `quick` and `war` modes. `meeting` and `darbar` route ministers through `MinisterVoice` (`persona/council/minister_voice.py`), which builds a doctrine-based LLM prompt per minister and returns structured `{stance, reasoning, confidence, warning, knowledge_cited}` JSON.
- *Observation*: `quick`/`war` remain deterministic by design; LLM deliberation is limited to the higher-stakes modes.

### 4. Reinforcement Learning (RL) Loops
The `decision_env/` directory contains `MultiStep` and `LongHorizon` simulation environments for training ERA policies, calculating rewards via `RewardModel`.
- *Observation*: The code to run the environment exists (`run_refactored.py`), but the actual RL agent training loop (e.g., updating PPO/DQN weights based on `StateTransition`) is externalized or not fully wired into the `policy_model/` and `value_model/` subdirectories.

### 5. Contract Validation is Permissive
The `ContractValidationModule` runs at Stage 10.
- *Observation*: Even when contracts fail validation, the pipeline treats this as a `DEGRADE` (warning) rather than an `ABORT`. The pipeline is highly permissive regarding structural integrity unless `orchestrator_strict=True` is explicitly set in the environment.

---

## 3. Structural Strengths

Despite the gaps, the structural foundation is exceptional for a production-grade architecture:
- **Impeccable Type Safety**: The `core/contracts/` layer enforces strict data boundaries.
- **Robust Normalization**: The boilerplate normalization (`_coerce_bool`, `_normalize_key_name`) ensures that dirty inputs from LLMs or users will not crash the pipeline.
- **Ablation Ready**: The `ExecutionConfig` allows testing the pipeline seamlessly without ministers or advanced predictors.
- **Observability**: `ExecutionContext.emit()` ensures that every state transition is logged and trackable for post-mortem analysis.
