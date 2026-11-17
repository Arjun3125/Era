# ERA Runtime Configuration Reference

> **Source**: `config/settings.py`, `modules/runtime_config/module.py`

---

## 1. Overview

The ERA pipeline configuration is centralized in the `RuntimeSettings` dataclass.
It defines global toggles, LLM adapter defaults, logging behaviors, and orchestration
strictness. Every value is strongly typed and normalized upon initialization.

The settings are loaded during **Stage 2: Runtime Config** of the pipeline via
the `RuntimeConfigModule`, emitting a `RuntimeConfigContract`.

---

## 2. Environment Variables

All settings can be overridden via `ERA_*` environment variables. The system
uses robust boolean parsing (`"1", "true", "yes", "on"` vs `"0", "false", "no", "off"`).

### Pipeline Toggles

| Setting | Type | Environment Variable | Default | Description |
|---|---|---|---|---|
| `decision_pipeline_enabled` | `bool` | `ERA_DECISION_PIPELINE_ENABLED` | `True` | Master toggle for the entire pipeline. |
| `orchestrator_strict` | `bool` | `ERA_ORCHESTRATOR_STRICT` | `False` | If `True`, any stage error (even `DEGRADE` policy) triggers an `ABORT`. |

### Model & Adapter Config

| Setting | Type | Environment Variable | Default | Description |
|---|---|---|---|---|
| `primary_model_name` | `str` | `ERA_PRIMARY_MODEL` | `llama3:8b` | The default LLM model for heavy lifting. |
| `fast_model_name` | `str` | `ERA_FAST_MODEL` | `llama3:8b` | Model used for quick modes or low-latency tasks. |
| `llm_temperature` | `float` | `ERA_LLM_TEMPERATURE` | `0.7` | Default temperature for generation. |
| `llm_max_tokens` | `int` | `ERA_LLM_MAX_TOKENS` | `1024` | Maximum token limit for standard completions. |

### Prediction & Router Flags

| Setting | Type | Environment Variable | Default | Description |
|---|---|---|---|---|
| `reasoning_controller_enabled` | `bool` | `ERA_REASONING_CONTROLLER_ENABLED` | `False` | Enables `ReasoningControllerPredictor` for token budget prediction. |
| `expert_router_enabled` | `bool` | `ERA_EXPERT_ROUTER_ENABLED` | `False` | Enables `ExpertRouterPredictor` for sub-task routing. |
| `moe_router_enabled` | `bool` | `ERA_MOE_ROUTER_ENABLED` | `False` | Enables `MoERouterPredictor` (Mixture of Experts) minister selection. |
| `council_weight_model_enabled` | `bool` | `ERA_COUNCIL_WEIGHT_MODEL_ENABLED` | `False` | Enables `CouncilWeightPredictor` to dynamically weight minister votes. |
| `mode_controller_enabled` | `bool` | `ERA_MODE_CONTROLLER_ENABLED` | `False` | Enables `ModeControllerPredictor` for automatic mode selection. |

### Decision Thresholds

| Setting | Type | Environment Variable | Default | Description |
|---|---|---|---|---|
| `risk_threshold` | `float` | `ERA_RISK_THRESHOLD` | `0.7` | The confidence score required to `accept` a recommendation. |
| `uncertainty_threshold` | `float` | `ERA_UNCERTAINTY_THRESHOLD` | `0.6` | Triggers mode escalation if exceeded. |

### Logging & Observability

| Setting | Type | Environment Variable | Default | Description |
|---|---|---|---|---|
| `log_level` | `str` | `ERA_LOG_LEVEL` | `INFO` | Console logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `enable_telemetry` | `bool` | `ERA_ENABLE_TELEMETRY` | `True` | Emits `PipelineTelemetryContract` with timing data. |
| `log_format` | `str` | `ERA_LOG_FORMAT` | `json` | Logging format format (`json` or `text`). |

### Simulation Variables (Not in `settings.py` but used across system)

| Setting | Description |
|---|---|
| `PERSONA_BG_WAIT` | Delay (in seconds) for background analysis loop. Default `1.0`. |
| `AUTOMATED_SIMULATION` | If set, triggers `SyntheticHumanSimulation` automated evaluation loop. |
| `ERA_AUTOMATED_MAX_TURNS` | Maximum number of turns an automated simulation should execute. |

---

## 3. Configuration Normalization

The `RuntimeSettings` class enforces strict normalization:

```python
# Boolean Normalization
"1", "true", "yes", "on" -> True
"0", "false", "no", "off" -> False

# Float Normalization
invalid floats, NaN, Inf -> Default Fallback

# Integer Normalization
invalid integers -> Default Fallback

# String Normalization
.strip() and lowercase where appropriate (e.g., log_level)
```

---

## 4. Execution Config (Mode Orchestrator)

Separately from `RuntimeSettings`, the `ModeOrchestrator` uses `ExecutionConfig` to 
define ablation constraints for specific runs.

```python
@dataclass
class ExecutionConfig:
    disable_ministers: bool = False
    disable_ml_prior: bool = False
    disable_kis: bool = False
    disable_pwm: bool = False
    force_mode: Optional[str] = None
    override_ministers: Optional[List[str]] = None
```

This allows the evaluation harness to easily test the pipeline with missing components 
to calculate value-added impact.
