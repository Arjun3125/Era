"""Central staged orchestration runtime.

This file introduces a non-invasive pipeline runner that can coexist with
current entrypoints. Existing systems are not rewired in this phase.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
import math
import time

from ..contracts.context import ExecutionContext
from ..contracts.events import EventLevel, EventType
from ..contracts.io import ErrorContract, InputContract


class RunStatus(str, Enum):
    """Overall run state."""

    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    ABORTED = "aborted"

    @classmethod
    def coerce(cls, value: Any) -> "RunStatus":
        if isinstance(value, cls):
            return value
        text = PipelineOrchestrator._normalize_text(value).lower()
        try:
            return cls(text)
        except Exception as exc:
            raise ValueError(f"Unsupported run status '{value}'.") from exc


class ErrorPolicy(str, Enum):
    """Stage failure handling strategy."""

    ABORT = "abort"
    DEGRADE = "degrade"


@dataclass
class StageOutcome:
    """Normalized output returned by a pipeline stage."""

    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    continue_pipeline: bool = True
    degraded: bool = False

    def __post_init__(self) -> None:
        self.outputs = PipelineOrchestrator._clone_mapping(self.outputs)
        self.errors = PipelineOrchestrator._normalize_errors(self.errors)
        self.continue_pipeline = bool(self.continue_pipeline)
        self.degraded = bool(self.degraded)


@dataclass(frozen=True)
class RegisteredStage:
    """Internal stage definition."""

    name: str
    handler: Callable[[ExecutionContext], Any]
    on_error: ErrorPolicy = ErrorPolicy.ABORT


@dataclass
class OrchestrationResult:
    """Final result for one pipeline run."""

    run_id: str
    status: RunStatus
    context: ExecutionContext
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    total_runtime_ms: float = 0.0

    def __post_init__(self) -> None:
        self.run_id = PipelineOrchestrator._normalize_text(self.run_id)
        self.status = RunStatus.coerce(self.status)
        if not isinstance(self.context, ExecutionContext):
            raise TypeError("OrchestrationResult.context must be ExecutionContext.")
        self.stage_timings_ms = PipelineOrchestrator._normalize_timings(self.stage_timings_ms)
        self.total_runtime_ms = PipelineOrchestrator._to_non_negative_finite_float(
            self.total_runtime_ms
        )


class PipelineOrchestrator:
    """Simple synchronous orchestrator with explicit stage boundaries."""

    def __init__(self, *, name: str = "era_pipeline", strict: bool = False):
        self.name = name
        self.strict = strict
        self._stages: List[RegisteredStage] = []

    def register_stage(
        self,
        name: str,
        handler: Callable[[ExecutionContext], Any],
        *,
        on_error: str = "abort",
    ) -> None:
        """Append a stage to the pipeline."""
        stage_name = self._normalize_stage_name(name)
        if not callable(handler):
            raise TypeError("Stage handler must be callable.")
        if stage_name in {stage.name for stage in self._stages}:
            raise ValueError(f"Stage '{stage_name}' is already registered.")
        policy = self._normalize_error_policy(on_error)
        self._stages.append(RegisteredStage(name=stage_name, handler=handler, on_error=policy))

    def list_stages(self) -> List[str]:
        """Return stage names in execution order."""
        return [stage.name for stage in self._stages]

    def run(
        self,
        input_contract: InputContract,
        *,
        config: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> OrchestrationResult:
        """Execute all stages against a single execution context."""
        if not isinstance(input_contract, InputContract):
            raise TypeError("input_contract must be an InputContract.")
        if config is not None and not isinstance(config, Mapping):
            raise TypeError("config must be a mapping when provided.")
        if metadata is not None and not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping when provided.")

        context = ExecutionContext(
            input_contract=input_contract,
            config=self._normalize_mapping(config),
            metadata=self._normalize_mapping(metadata),
        )
        run_started = time.perf_counter()
        timings: Dict[str, float] = {}
        aborted = False

        context.emit(
            EventType.RUN_STARTED,
            payload={
                "pipeline": self.name,
                "stage_count": len(self._stages),
                "stages": self.list_stages(),
            },
            level=EventLevel.INFO,
        )

        for stage in self._stages:
            context.current_stage = stage.name
            context.emit(EventType.STAGE_STARTED, stage=stage.name)
            started = time.perf_counter()

            try:
                raw_result = stage.handler(context)
                outcome = self._normalize_outcome(raw_result)
            except Exception as exc:  # pragma: no cover - defensive branch
                outcome = StageOutcome(
                    errors=[f"{type(exc).__name__}: {exc}"],
                    continue_pipeline=(stage.on_error == ErrorPolicy.DEGRADE),
                    degraded=(stage.on_error == ErrorPolicy.DEGRADE),
                )
            outcome = self._sanitize_outcome(outcome, stage_name=stage.name)

            elapsed_ms = (time.perf_counter() - started) * 1000.0
            timings[stage.name] = round(elapsed_ms, 3)

            for key, value in outcome.outputs.items():
                context.state[key] = value

            stage_recoverable = bool(stage.on_error == ErrorPolicy.DEGRADE and not self.strict)
            for message in outcome.errors:
                context.add_error(
                    ErrorContract(
                        code="stage_error",
                        message=message,
                        stage=stage.name,
                        recoverable=stage_recoverable,
                    )
                )

            has_errors = bool(outcome.errors)
            is_degraded = bool(outcome.degraded) or (
                has_errors and stage.on_error == ErrorPolicy.DEGRADE and not self.strict
            )

            if has_errors or is_degraded:
                event_type = (
                    EventType.STAGE_DEGRADED
                    if is_degraded
                    else EventType.STAGE_FAILED
                )
                context.emit(
                    event_type,
                    stage=stage.name,
                    payload={
                        "errors": list(outcome.errors),
                        "elapsed_ms": timings.get(stage.name, 0.0),
                        "output_count": len(outcome.outputs),
                        "continue_pipeline": bool(outcome.continue_pipeline),
                        "degraded": bool(outcome.degraded),
                    },
                    level=(
                        EventLevel.WARNING
                        if event_type == EventType.STAGE_DEGRADED
                        else EventLevel.ERROR
                    ),
                )
            else:
                context.emit(
                    EventType.STAGE_COMPLETED,
                    stage=stage.name,
                    payload={
                        "elapsed_ms": timings.get(stage.name, 0.0),
                        "output_count": len(outcome.outputs),
                    },
                    level=EventLevel.INFO,
                )

            should_abort = bool(
                (has_errors and stage.on_error == ErrorPolicy.ABORT)
                or (self.strict and has_errors and stage.on_error == ErrorPolicy.DEGRADE)
                or (self.strict and outcome.degraded and not has_errors)
            )
            if should_abort:
                aborted = True
                break

            if not outcome.continue_pipeline:
                break

        if aborted:
            status = RunStatus.ABORTED
            context.emit(
                EventType.RUN_ABORTED,
                payload={"error_count": len(context.errors)},
                level=EventLevel.ERROR,
            )
        elif context.errors:
            status = RunStatus.COMPLETED_WITH_ERRORS
            context.emit(
                EventType.RUN_COMPLETED,
                payload={"status": status.value, "error_count": len(context.errors)},
                level=EventLevel.WARNING,
            )
        else:
            status = RunStatus.COMPLETED
            context.emit(
                EventType.RUN_COMPLETED,
                payload={"status": status.value},
                level=EventLevel.INFO,
            )

        total_runtime_ms = round((time.perf_counter() - run_started) * 1000.0, 3)

        return OrchestrationResult(
            run_id=context.run_id,
            status=status,
            context=context,
            stage_timings_ms=timings,
            total_runtime_ms=total_runtime_ms,
        )

    @staticmethod
    def _normalize_outcome(raw_result: Any) -> StageOutcome:
        """Allow stage implementations to return a dict or StageOutcome."""
        if raw_result is None:
            return StageOutcome()
        if isinstance(raw_result, StageOutcome):
            return raw_result
        if isinstance(raw_result, Mapping):
            return StageOutcome(outputs=PipelineOrchestrator._clone_mapping(raw_result))
        raise TypeError(
            "Stage handlers must return StageOutcome, dict, or None."
        )

    @staticmethod
    def _sanitize_outcome(outcome: StageOutcome, *, stage_name: str) -> StageOutcome:
        warnings: List[str] = []

        outputs_raw = outcome.outputs
        outputs = PipelineOrchestrator._normalize_outputs(outputs_raw)
        if outputs_raw is not None and not isinstance(outputs_raw, Mapping):
            warnings.append(
                "orchestrator_invalid_stage_outputs:"
                f"stage={stage_name},type={type(outputs_raw).__name__}"
            )
        elif isinstance(outputs_raw, Mapping):
            normalized_output_keys: List[str] = []
            for raw_key, _ in PipelineOrchestrator._coerce_mapping_items(outputs_raw) or []:
                normalized = PipelineOrchestrator._normalize_text(raw_key)
                if normalized:
                    normalized_output_keys.append(normalized)
            if len(set(normalized_output_keys)) != len(normalized_output_keys):
                warnings.append(
                    "orchestrator_output_key_collision_after_stringify:"
                    f"stage={stage_name}"
                )

        errors_raw = outcome.errors
        normalized_errors: List[str] = PipelineOrchestrator._normalize_errors(errors_raw)

        if warnings:
            normalized_errors.extend(warnings)

        deduped_errors: List[str] = []
        seen = set()
        for item in normalized_errors:
            if item in seen:
                continue
            seen.add(item)
            deduped_errors.append(item)

        return StageOutcome(
            outputs=outputs,
            errors=deduped_errors,
            continue_pipeline=bool(outcome.continue_pipeline),
            degraded=bool(outcome.degraded),
        )

    @staticmethod
    def _normalize_stage_name(value: Any) -> str:
        name = PipelineOrchestrator._normalize_text(value)
        if not name:
            raise ValueError("Stage name must be non-empty.")
        return name

    @staticmethod
    def _normalize_error_policy(value: Any) -> ErrorPolicy:
        text = PipelineOrchestrator._normalize_text(value).lower()
        try:
            return ErrorPolicy(text)
        except Exception as exc:
            raise ValueError("on_error must be 'abort' or 'degrade'.") from exc

    @staticmethod
    def _coerce_iterable_items(value: Any, *, preserve_partial: bool) -> tuple[List[Any], bool]:
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

    @staticmethod
    def _clone_mapping(value: Any) -> Dict[Any, Any]:
        items = PipelineOrchestrator._coerce_mapping_items(value)
        if items is None:
            return {}
        cloned: Dict[Any, Any] = {}
        for raw_key, item_value in items:
            cloned[raw_key] = item_value
        return cloned

    @staticmethod
    def _normalize_mapping(value: Any) -> Dict[str, Any]:
        items = PipelineOrchestrator._coerce_mapping_items(value)
        if items is None:
            return {}
        normalized: Dict[str, Any] = {}
        for raw_key, item in items:
            key = PipelineOrchestrator._normalize_text(raw_key)
            if not key:
                continue
            normalized[key] = item
        return normalized

    @staticmethod
    def _normalize_outputs(value: Any) -> Dict[str, Any]:
        return PipelineOrchestrator._normalize_mapping(value)

    @staticmethod
    def _normalize_errors(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
            return [text] if text else []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, Mapping):
            text = PipelineOrchestrator._coerce_error_text(value)
            return [text] if text else []
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            items, failed = PipelineOrchestrator._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not items:
                text = PipelineOrchestrator._coerce_error_text(value)
                return [text] if text else []
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            items, failed = PipelineOrchestrator._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not items:
                text = PipelineOrchestrator._coerce_error_text(value)
                return [text] if text else []
        else:
            text = PipelineOrchestrator._coerce_error_text(value)
            return [text] if text else []
        normalized: List[str] = []
        seen = set()
        for item in items:
            text = PipelineOrchestrator._coerce_error_text(item)
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _normalize_timings(value: Any) -> Dict[str, float]:
        if not isinstance(value, Mapping):
            return {}
        normalized: Dict[str, float] = {}
        try:
            raw_items = value.items()
        except Exception:
            return {}
        items, _ = PipelineOrchestrator._coerce_iterable_items(raw_items, preserve_partial=True)
        for raw_name, raw_timing in items:
            stage = PipelineOrchestrator._normalize_text(raw_name)
            if not stage:
                continue
            timing = PipelineOrchestrator._to_non_negative_finite_float(raw_timing)
            normalized[stage] = round(timing, 3)
        return normalized

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _coerce_error_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        if isinstance(value, Mapping):
            for key in ("message", "error", "detail", "code"):
                candidate = PipelineOrchestrator._read_mapping_field(value, (key,))
                text = PipelineOrchestrator._normalize_text(candidate)
                if text:
                    return text
            return PipelineOrchestrator._normalize_text(PipelineOrchestrator._clone_mapping(value))
        return PipelineOrchestrator._normalize_text(value)

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            PipelineOrchestrator._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _read_mapping_field(
        source: Mapping[str, Any],
        keys: Sequence[str],
        *,
        default: Any = None,
    ) -> Any:
        if not isinstance(source, Mapping):
            return default
        normalized_targets = {
            PipelineOrchestrator._normalize_key_name(key)
            for key in keys
        }
        try:
            raw_items = source.items()
        except Exception:
            return default
        items, _ = PipelineOrchestrator._coerce_iterable_items(raw_items, preserve_partial=True)
        for raw_key, value in items:
            if PipelineOrchestrator._normalize_key_name(raw_key) in normalized_targets:
                return value
        return default

    @staticmethod
    def _coerce_mapping_items(value: Any) -> List[tuple[Any, Any]] | None:
        if value is None:
            return []
        if isinstance(value, Mapping):
            try:
                raw_items = value.items()
            except Exception:
                return []
            items, _ = PipelineOrchestrator._coerce_iterable_items(
                raw_items,
                preserve_partial=True,
            )
            return [(key, item_value) for key, item_value in items]
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items, failed = PipelineOrchestrator._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not raw_items:
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

    @staticmethod
    def _to_non_negative_finite_float(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if not math.isfinite(numeric):
            return 0.0
        if numeric < 0.0:
            return 0.0
        return numeric
