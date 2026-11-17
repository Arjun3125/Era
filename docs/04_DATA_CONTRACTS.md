# ERA Data Contracts Reference

> **Source**: `core/contracts/io.py`, `core/contracts/context.py`,
> `core/contracts/events.py`, `core/contracts/module.py`

---

## 1. Contract Philosophy

All ERA data contracts are Python `@dataclass` objects with strict validation
in `__post_init__`. Every field undergoes normalization:

- **Strings**: `.strip()`, empty → default, bytes → UTF-8 decoded
- **Floats**: `math.isfinite()` check, clamped to [0.0, 1.0] for confidence
- **Booleans**: Accepts `True/False/1/0/"true"/"false"/"yes"/"no"/"on"/"off"`
- **Mappings**: Iterable-safe coercion, key deduplication, empty-key filtering
- **Lists**: Iterable coercion with `preserve_partial` support
- **Enums**: Case-insensitive coercion with alias tables

---

## 2. Core IO Contracts

### `InputContract`

```python
@dataclass
class InputContract:
    user_input: str          # Required. Non-empty after strip.
    session_id: str          # UUID string, auto-generated if empty.
    metadata: Dict[str, Any] # Arbitrary key-value pairs. Default: {}
```

**Validation**: `user_input` must be non-empty string. `session_id` defaults to
`uuid.uuid4()`. `metadata` coerced to `Dict[str, Any]`.

---

### `DecisionContract`

```python
@dataclass
class DecisionContract:
    decision: str            # "accept" | "accept_with_mitigation" | "defer" | "reject" | "direct_response"
    confidence: float        # [0.0, 1.0] — clamped
    rationale: str           # Human-readable explanation
    mode: str                # Resolved mode name
    metadata: Dict[str, Any] # Includes council_outcome, council_recommendation, context_keys, warning_count
```

---

### `ErrorContract`

```python
@dataclass
class ErrorContract:
    code: str                # Error classification ("stage_error", "runtime_error", etc.)
    message: str             # Human-readable error description
    stage: Optional[str]     # Pipeline stage where error occurred
    recoverable: bool        # Whether pipeline can continue (default: False)
    details: Dict[str, Any]  # Extra diagnostic info. Default: {}
```

---

### `ModeResolutionContract`

```python
@dataclass
class ModeResolutionContract:
    mode: str                      # Resolved mode name
    should_invoke_council: bool    # Whether council deliberation is needed
    selected_ministers: List[str]  # Minister names to activate
    rationale: str                 # Reason for mode selection
    confidence: float              # [0.0, 1.0]
```

---

### `DomainAnalysisContract`

```python
@dataclass
class DomainAnalysisContract:
    domains: List[str]       # Detected domain categories
    confidence: float        # [0.0, 1.0]
    source: str              # Classification method
```

---

### `KnowledgeContract`

```python
@dataclass
class KnowledgeContract:
    synthesized_knowledge: List[Any]  # Knowledge items
    sources: List[str]                # Knowledge sources
    metadata: Dict[str, Any]          # Synthesis metadata
```

---

### `CouncilContract`

```python
@dataclass
class CouncilContract:
    outcome: str                        # "consensus_reached" | "bounded_risk_tradeoff" | "deadlocked" | ...
    recommendation: str                 # "support" | "oppose" | "defer" | specialized tokens
    consensus_strength: float           # [0.0, 1.0]
    avg_confidence: float               # [0.0, 1.0]
    reasoning: str                      # Aggregated reasoning text (max 1000 chars)
    minister_positions: Dict[str, Any]  # Per-minister stance/confidence/reasoning
    red_line_concerns: List[str]        # Ministers that triggered red lines
    mode: str                           # Mode under which council convened
```

---

### `CouncilNormalizationContract`

Normalized variant of `CouncilContract` with canonical field values.

---

### `RuntimeConfigContract`

Snapshot of the loaded runtime configuration at pipeline start.

---

### `RequestContextContract`

Request-level metadata enrichment.

---

### `DecisionPackagingContract`

Final assembled decision envelope.

---

### `ContractValidationContract`

Schema compliance results.

---

### `PipelineTelemetryContract`

```python
@dataclass
class PipelineTelemetryContract:
    stage_timings_ms: Dict[str, float]  # Per-stage execution time in ms
    total_runtime_ms: float             # Total pipeline runtime in ms
```

---

### `PipelineErrorSummaryContract`

Aggregated error roll-up across all stages.

---

### `PipelineIssueContract`

Individual pipeline issue record.

---

## 3. Context Contracts

### `ExecutionContext`

```python
@dataclass
class ExecutionContext:
    input_contract: InputContract       # Required. Validated on init.
    config: Dict[str, Any]              # Pipeline configuration
    run_id: str                         # UUID, auto-generated
    started_at: str                     # ISO 8601 timestamp (UTC)
    metadata: Dict[str, Any]            # Run-level metadata
    state: Dict[str, Any]              # Mutable state bag (stages write here)
    events: List[EventRecord]          # Emitted event records
    errors: List[ErrorContract]        # Accumulated errors
    current_stage: Optional[str]       # Currently executing stage name
```

**Key Methods**:
- `emit(event_type, *, payload, stage, level)` → `EventRecord`
- `add_error(error)` → appends to `self.errors`

---

## 4. Event Contracts

### `EventType` (Enum)

| Value | Description |
|---|---|
| `run_started` | Pipeline execution begins |
| `stage_started` | Individual stage begins |
| `stage_completed` | Stage finishes successfully |
| `stage_failed` | Stage fails (abort policy) |
| `stage_degraded` | Stage fails (degrade policy) |
| `run_completed` | Pipeline finishes |
| `run_aborted` | Pipeline aborted due to error |

**Aliases**: `runstart`→`run_started`, `stage_done`→`stage_completed`,
`stage_error`→`stage_failed`, etc.

### `EventLevel` (Enum)

| Value | Aliases |
|---|---|
| `info` | `information` |
| `warning` | `warn` |
| `error` | `err`, `fatal` |

### `EventRecord`

```python
@dataclass(frozen=True)
class EventRecord:
    run_id: str
    event_type: EventType
    payload: Dict[str, Any]     # Event-specific data
    stage: Optional[str]
    level: EventLevel
    event_id: str               # UUID
    timestamp: str              # ISO 8601
```

---

## 5. Module Contracts

### `ModulePlugin` (Protocol)

```python
class ModulePlugin(Protocol):
    def name(self) -> str: ...
    def capabilities(self) -> Mapping[str, Any]: ...
    def validate(self, context: ExecutionContext) -> None: ...
    def execute(self, context: ExecutionContext) -> ModuleResult: ...
    def health(self) -> ModuleHealth: ...
```

### `ModuleResult`

```python
@dataclass
class ModuleResult:
    status: ModuleStatus        # SUCCESS | DEGRADED | FAILED
    outputs: Dict[str, Any]     # Written to ExecutionContext.state
    metrics: Dict[str, Any]     # Stage-level metrics
    errors: list[str]           # Error messages
```

### `ModuleStatus` (Enum)

| Value | Aliases |
|---|---|
| `success` | `ok`, `pass` |
| `degraded` | `warning`, `warn` |
| `failed` | `error` |

### `ModuleHealth`

```python
@dataclass
class ModuleHealth:
    ok: bool
    details: Dict[str, Any]
```

---

## 6. Orchestration Contracts

### `StageOutcome`

```python
@dataclass
class StageOutcome:
    outputs: Dict[str, Any]    # Key-value outputs to merge into context.state
    errors: List[str]          # Error messages
    continue_pipeline: bool    # Whether next stage should execute
    degraded: bool             # Whether this stage degraded
```

### `OrchestrationResult`

```python
@dataclass
class OrchestrationResult:
    run_id: str
    status: RunStatus           # COMPLETED | COMPLETED_WITH_ERRORS | ABORTED
    context: ExecutionContext
    stage_timings_ms: Dict[str, float]
    total_runtime_ms: float
```

### `RunStatus` (Enum)

| Value | Description |
|---|---|
| `completed` | All stages passed |
| `completed_with_errors` | Some stages degraded |
| `aborted` | Pipeline halted on error |

---

## 7. Prime Decision Contracts

### `PrimeDecisionResult`

```python
@dataclass
class PrimeDecisionResult:
    final_decision: Dict[str, Any]               # {final_outcome, reason, confidence, details}
    decision_contract: DecisionContract           # Typed contract
    normalized_council: Dict[str, Any]            # Canonical council payload
    normalized_minister_outputs: Dict[str, Dict]  # Per-minister normalized
    warnings: List[str]                            # Normalization warnings
```
