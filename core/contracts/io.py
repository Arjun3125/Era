"""Typed data flow contracts for the unified decision pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _as_str(value: Any, *, default: str = "") -> str:
    if value is None:
        text = ""
    elif isinstance(value, (bytes, bytearray)):
        text = bytes(value).decode("utf-8", errors="replace").strip()
    else:
        text = str(value).strip()
    return text or default


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        text = ""
    elif isinstance(value, (bytes, bytearray)):
        text = bytes(value).decode("utf-8", errors="replace").strip()
    else:
        text = str(value).strip()
    return text or None


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
    if isinstance(value, (bytes, bytearray)):
        text = bytes(value).decode("utf-8", errors="replace").strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
    return default


def _as_int(value: Any, *, default: int, minimum: int | None = None) -> int:
    try:
        numeric = int(value)
    except Exception:
        numeric = default
    if minimum is not None and numeric < minimum:
        return minimum
    return numeric


def _as_float(value: Any, *, default: float, minimum: float | None = None) -> float:
    try:
        numeric = float(value)
    except Exception:
        numeric = default
    if not math.isfinite(numeric):
        numeric = default
    if minimum is not None and numeric < minimum:
        return minimum
    return numeric


def _coerce_iterable_items(
    value: Any,
    *,
    preserve_partial: bool,
) -> tuple[List[Any], bool]:
    try:
        iterator = iter(value)
    except Exception:
        return [], True
    items: List[Any] = []
    failed = False
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            break
        except Exception:
            failed = True
            break
        items.append(item)
    if failed and not preserve_partial:
        return [], True
    return items, failed


def _coerce_mapping_items(value: Any) -> List[tuple[Any, Any]] | None:
    if isinstance(value, Mapping):
        try:
            return list(value.items())
        except Exception:
            return []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
            return None
        items: List[tuple[Any, Any]] = []
        for raw_item in raw_items:
            try:
                key, item_value = raw_item
            except Exception:
                return None
            items.append((key, item_value))
        return items
    return None


def _as_mapping(value: Any) -> Dict[str, Any]:
    items = _coerce_mapping_items(value)
    if items is None:
        return {}
    normalized: Dict[str, Any] = {}
    for raw_key, item in items:
        key = _as_str(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = item
    return normalized


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    if isinstance(value, Iterable) and not isinstance(
        value,
        (str, bytes, bytearray, Mapping),
    ):
        items, _ = _coerce_iterable_items(value, preserve_partial=True)
        return items
    return []


def _as_str_list(value: Any) -> List[str]:
    items = _as_list(value)
    normalized: List[str] = []
    seen = set()
    for item in items:
        text = _as_str(item)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _as_trace_list(value: Any) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    for item in _as_list(value):
        if isinstance(item, Mapping):
            trace.append(_as_mapping(item))
    return trace


def _as_float_mapping(value: Any) -> Dict[str, float]:
    mapping = _as_mapping(value)
    normalized: Dict[str, float] = {}
    for key, raw in mapping.items():
        numeric = _as_float(raw, default=float("nan"))
        if not math.isfinite(numeric):
            continue
        normalized[key] = numeric
    return normalized


@dataclass
class InputContract:
    """Canonical run input consumed by the central orchestrator."""

    user_input: str
    source: str = "interactive"
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        self.user_input = _as_str(self.user_input)
        self.source = _as_str(self.source, default="interactive")
        self.session_id = _as_optional_str(self.session_id)
        self.metadata = _as_mapping(self.metadata)
        self.timestamp = _as_str(
            self.timestamp,
            default=datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class RuntimeConfigContract:
    """Resolved runtime configuration shared across pipeline stages."""

    app_name: str = "era"
    environment: str = "development"
    orchestrator_strict: bool = False
    decision_pipeline_enabled: bool = True

    observability_enabled: bool = True
    observability_emit_events: bool = False
    observability_emit_summary: bool = True
    observability_write_file: bool = False
    observability_stderr: bool = False
    observability_file: str = "logs/orchestration_events.jsonl"

    source: str = "environment"
    overrides_applied: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Preserve explicit empty strings so runtime settings layer can emit
        # normalization warnings with source context.
        self.app_name = _as_str(self.app_name, default="")
        self.environment = _as_str(self.environment, default="")
        self.orchestrator_strict = _as_bool(self.orchestrator_strict, default=False)
        self.decision_pipeline_enabled = _as_bool(self.decision_pipeline_enabled, default=True)
        self.observability_enabled = _as_bool(self.observability_enabled, default=True)
        self.observability_emit_events = _as_bool(self.observability_emit_events, default=False)
        self.observability_emit_summary = _as_bool(self.observability_emit_summary, default=True)
        self.observability_write_file = _as_bool(self.observability_write_file, default=False)
        self.observability_stderr = _as_bool(self.observability_stderr, default=False)
        self.observability_file = _as_str(self.observability_file, default="")
        self.source = _as_str(self.source, default="environment")
        self.overrides_applied = _as_str_list(self.overrides_applied)


@dataclass
class PipelineTelemetryContract:
    """Post-run telemetry summary for one orchestrated pipeline execution."""

    status: str = "unknown"
    stage_count: int = 0
    event_count: int = 0
    error_count: int = 0
    total_stage_ms: float = 0.0
    slowest_stage: str = ""
    slowest_stage_ms: float = 0.0
    incomplete_stages: List[str] = field(default_factory=list)
    emitted_events: int = 0
    emitted_summary: bool = False
    source: str = "decision_pipeline"

    def __post_init__(self) -> None:
        self.status = _as_str(self.status, default="unknown")
        self.stage_count = _as_int(self.stage_count, default=0, minimum=0)
        self.event_count = _as_int(self.event_count, default=0, minimum=0)
        self.error_count = _as_int(self.error_count, default=0, minimum=0)
        self.total_stage_ms = _as_float(self.total_stage_ms, default=0.0, minimum=0.0)
        self.slowest_stage = _as_str(self.slowest_stage)
        self.slowest_stage_ms = _as_float(self.slowest_stage_ms, default=0.0, minimum=0.0)
        self.incomplete_stages = _as_str_list(self.incomplete_stages)
        self.emitted_events = _as_int(self.emitted_events, default=0, minimum=0)
        self.emitted_summary = _as_bool(self.emitted_summary, default=False)
        self.source = _as_str(self.source, default="decision_pipeline")


@dataclass
class PipelineIssueContract:
    """Normalized issue record derived from runtime and module failures."""

    code: str
    message: str
    severity: str = "error"
    stage: Optional[str] = None
    recoverable: bool = False
    source: str = "decision_pipeline"
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.code = _as_str(self.code, default="pipeline_issue")
        self.message = _as_str(self.message, default="unspecified_issue")
        severity = _as_str(self.severity, default="error").lower()
        self.severity = severity if severity in {"warning", "error"} else "error"
        self.stage = _as_optional_str(self.stage)
        self.recoverable = _as_bool(self.recoverable, default=False)
        self.source = _as_str(self.source, default="decision_pipeline")
        self.details = _as_mapping(self.details)


@dataclass
class PipelineErrorSummaryContract:
    """Aggregate error/warning counts for one pipeline run."""

    issue_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    recoverable_count: int = 0
    fatal_count: int = 0
    has_fatal: bool = False
    stages_with_issues: List[str] = field(default_factory=list)
    source: str = "decision_pipeline"

    def __post_init__(self) -> None:
        self.issue_count = _as_int(self.issue_count, default=0, minimum=0)
        self.error_count = _as_int(self.error_count, default=0, minimum=0)
        self.warning_count = _as_int(self.warning_count, default=0, minimum=0)
        self.recoverable_count = _as_int(self.recoverable_count, default=0, minimum=0)
        self.fatal_count = _as_int(self.fatal_count, default=0, minimum=0)
        self.has_fatal = _as_bool(self.has_fatal, default=(self.fatal_count > 0))
        if self.fatal_count > 0:
            self.has_fatal = True
        self.stages_with_issues = _as_str_list(self.stages_with_issues)
        self.source = _as_str(self.source, default="decision_pipeline")


@dataclass
class RequestContextContract:
    """Canonical normalized request context for pipeline execution."""

    requested_mode: str = "meeting"
    routing_context: Dict[str, Any] = field(default_factory=dict)
    warning_count: int = 0
    source: str = "input_normalization"

    def __post_init__(self) -> None:
        self.requested_mode = _as_str(self.requested_mode, default="meeting").lower()
        self.routing_context = _as_mapping(self.routing_context)
        self.warning_count = _as_int(self.warning_count, default=0, minimum=0)
        self.source = _as_str(self.source, default="input_normalization")


@dataclass
class ContractValidationContract:
    """Validation summary for inter-stage contract consistency checks."""

    passed: bool = True
    warning_count: int = 0
    error_count: int = 0
    warning_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    checks: Dict[str, str] = field(default_factory=dict)
    source: str = "contract_validation"

    def __post_init__(self) -> None:
        self.passed = _as_bool(self.passed, default=True)
        self.warning_count = _as_int(self.warning_count, default=0, minimum=0)
        self.error_count = _as_int(self.error_count, default=0, minimum=0)
        self.warning_checks = _as_str_list(self.warning_checks)
        self.failed_checks = _as_str_list(self.failed_checks)
        self.checks = {key: _as_str(value) for key, value in _as_mapping(self.checks).items()}
        self.source = _as_str(self.source, default="contract_validation")


@dataclass
class CouncilNormalizationContract:
    """Normalization summary for council outputs consumed by prime decision."""

    mode: str = "meeting"
    outcome: str = "not_invoked"
    recommendation: str = "defer"
    consensus_strength: float = 0.0
    minister_count: int = 0
    failed_minister_count: int = 0
    red_line_count: int = 0
    council_invoked: bool = False
    warning_count: int = 0
    source: str = "council_normalization"

    def __post_init__(self) -> None:
        self.mode = _as_str(self.mode, default="meeting").lower()
        self.outcome = _as_str(self.outcome, default="not_invoked")
        self.recommendation = _as_str(self.recommendation, default="defer")
        self.consensus_strength = _as_float(self.consensus_strength, default=0.0, minimum=0.0)
        self.minister_count = _as_int(self.minister_count, default=0, minimum=0)
        self.failed_minister_count = _as_int(self.failed_minister_count, default=0, minimum=0)
        self.red_line_count = _as_int(self.red_line_count, default=0, minimum=0)
        self.council_invoked = _as_bool(self.council_invoked, default=False)
        self.warning_count = _as_int(self.warning_count, default=0, minimum=0)
        self.source = _as_str(self.source, default="council_normalization")


@dataclass
class DecisionPackagingContract:
    """Final packaged decision summary contract for downstream consumption."""

    final_outcome: str = "defer"
    mode: str = "meeting"
    confidence: float = 0.0
    recommendation: str = "defer"
    council_outcome: str = "not_invoked"
    red_line_count: int = 0
    knowledge_item_count: int = 0
    requires_followup: bool = False
    warning_count: int = 0
    source: str = "decision_packaging"

    def __post_init__(self) -> None:
        self.final_outcome = _as_str(self.final_outcome, default="defer")
        self.mode = _as_str(self.mode, default="meeting").lower()
        self.confidence = _as_float(self.confidence, default=0.0, minimum=0.0)
        self.recommendation = _as_str(self.recommendation, default="defer")
        self.council_outcome = _as_str(self.council_outcome, default="not_invoked")
        self.red_line_count = _as_int(self.red_line_count, default=0, minimum=0)
        self.knowledge_item_count = _as_int(self.knowledge_item_count, default=0, minimum=0)
        self.requires_followup = _as_bool(self.requires_followup, default=False)
        self.warning_count = _as_int(self.warning_count, default=0, minimum=0)
        self.source = _as_str(self.source, default="decision_packaging")


@dataclass
class ModeResolutionContract:
    """Resolved mode decision and routing metadata."""

    mode: str
    should_invoke_council: bool
    selected_ministers: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.0

    def __post_init__(self) -> None:
        self.mode = _as_str(self.mode, default="meeting").lower()
        self.should_invoke_council = _as_bool(self.should_invoke_council, default=False)
        self.selected_ministers = _as_str_list(self.selected_ministers)
        self.rationale = _as_str(self.rationale)
        self.confidence = _as_float(self.confidence, default=0.0, minimum=0.0)


@dataclass
class DomainAnalysisContract:
    """Normalized domain analysis envelope for routing and synthesis stages."""

    domains: List[str] = field(default_factory=list)
    domain_confidence: float = 0.0
    stakes: str = "medium"
    reversibility: str = "partially_reversible"
    key_entities: List[str] = field(default_factory=list)
    domain_scores: Dict[str, float] = field(default_factory=dict)
    source: str = "heuristic"

    def __post_init__(self) -> None:
        self.domains = [item.lower() for item in _as_str_list(self.domains)]
        self.domain_confidence = _as_float(self.domain_confidence, default=0.0, minimum=0.0)
        self.stakes = _as_str(self.stakes, default="medium")
        self.reversibility = _as_str(self.reversibility, default="partially_reversible")
        self.key_entities = _as_str_list(self.key_entities)
        self.domain_scores = _as_float_mapping(self.domain_scores)
        self.source = _as_str(self.source, default="heuristic")


@dataclass
class KnowledgeContract:
    """Knowledge retrieval/synthesis output that feeds deliberation."""

    active_domains: List[str] = field(default_factory=list)
    synthesized_items: List[str] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    quality: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.active_domains = _as_str_list(self.active_domains)
        self.synthesized_items = _as_str_list(self.synthesized_items)
        self.trace = _as_trace_list(self.trace)
        self.quality = _as_mapping(self.quality)


@dataclass
class CouncilContract:
    """Council execution outcome used by decision finalization."""

    outcome: str = "not_invoked"
    recommendation: str = "defer"
    consensus_strength: float = 0.0
    minister_positions: Dict[str, Any] = field(default_factory=dict)
    red_line_concerns: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.outcome = _as_str(self.outcome, default="not_invoked")
        self.recommendation = _as_str(self.recommendation, default="defer")
        self.consensus_strength = _as_float(self.consensus_strength, default=0.0, minimum=0.0)
        self.minister_positions = _as_mapping(self.minister_positions)
        self.red_line_concerns = _as_str_list(self.red_line_concerns)


@dataclass
class DecisionContract:
    """Final decision output of the orchestrator."""

    decision: str
    confidence: float = 0.0
    rationale: str = ""
    mode: str = "meeting"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.decision = _as_str(self.decision, default="defer")
        self.confidence = _as_float(self.confidence, default=0.0, minimum=0.0)
        self.rationale = _as_str(self.rationale)
        self.mode = _as_str(self.mode, default="meeting").lower()
        self.metadata = _as_mapping(self.metadata)


@dataclass
class ErrorContract:
    """Error envelope used for stage and run level failures."""

    code: str
    message: str
    stage: Optional[str] = None
    recoverable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.code = _as_str(self.code, default="runtime_error")
        self.message = _as_str(self.message, default="unspecified_error")
        self.stage = _as_optional_str(self.stage)
        self.recoverable = _as_bool(self.recoverable, default=False)
        self.details = _as_mapping(self.details)
