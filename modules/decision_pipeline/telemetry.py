"""Post-run telemetry collection and emission for decision pipeline runs."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, List, Mapping

from config import RuntimeSettings
from core.contracts import PipelineTelemetryContract, RuntimeConfigContract
from core.observability import EventTraceBuilder, OrchestrationMetrics, StructuredEventLogger
from core.orchestrator import OrchestrationResult


@dataclass
class DecisionPipelineTelemetryResult:
    """Telemetry payload emitted after one pipeline run."""

    contract: PipelineTelemetryContract
    metrics: Dict[str, Any]
    trace: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)


@dataclass
class DecisionPipelineTelemetryEngine:
    """Computes metrics/trace and emits telemetry from runtime config flags."""

    metrics_builder_factory: Callable[[], OrchestrationMetrics] = OrchestrationMetrics
    trace_builder_factory: Callable[[], EventTraceBuilder] = EventTraceBuilder
    logger_factory: Callable[[RuntimeSettings], Any] = StructuredEventLogger
    sanitize_max_depth: int = 6
    sanitize_max_items: int = 200
    sanitize_max_string: int = 4000

    def collect(
        self,
        *,
        result: OrchestrationResult,
        runtime_config: RuntimeConfigContract,
        metadata: Mapping[str, Any] | None = None,
    ) -> DecisionPipelineTelemetryResult:
        warnings: List[str] = []
        runtime_contract = self._normalize_runtime_contract(
            runtime_config,
            warnings=warnings,
        )
        metrics = self._collect_metrics(result=result, warnings=warnings)
        trace = self._collect_trace(result=result, warnings=warnings)

        self._check_trace_consistency(metrics=metrics, trace=trace, warnings=warnings)

        emitted_events = 0
        emitted_summary = False

        safe_metrics = self._ensure_mapping(
            self._sanitize_payload(
                metrics,
                path="metrics",
                warnings=warnings,
                max_depth=self.sanitize_max_depth,
                max_items=self.sanitize_max_items,
                max_string=self.sanitize_max_string,
            ),
            name="metrics",
            warnings=warnings,
        )
        safe_trace = self._ensure_mapping(
            self._sanitize_payload(
                trace,
                path="trace",
                warnings=warnings,
                max_depth=self.sanitize_max_depth,
                max_items=self.sanitize_max_items,
                max_string=self.sanitize_max_string,
            ),
            name="trace",
            warnings=warnings,
        )
        safe_metadata = self._sanitize_metadata(metadata=metadata, warnings=warnings)

        if runtime_contract.observability_enabled:
            runtime_settings = self._runtime_settings_from_contract(
                runtime_config=runtime_contract,
                warnings=warnings,
            )
            logger = self._build_logger(runtime_settings=runtime_settings, warnings=warnings)
            if logger is not None:
                if runtime_settings.observability_emit_events:
                    emitted_events = self._emit_events(
                        logger=logger,
                        result=result,
                        warnings=warnings,
                    )

                if runtime_settings.observability_emit_summary:
                    emitted_summary = self._emit_summary(
                        logger=logger,
                        result=result,
                        runtime_config=runtime_contract,
                        metrics=safe_metrics,
                        trace=safe_trace,
                        metadata=safe_metadata,
                        warnings=warnings,
                    )

        warnings = self._dedupe_warnings(warnings)
        status_default = str(getattr(result.status, "value", result.status))

        contract = PipelineTelemetryContract(
            status=str(safe_metrics.get("status", status_default)),
            stage_count=self._to_int(safe_metrics.get("stage_count"), default=0),
            event_count=self._to_int(safe_metrics.get("event_count"), default=0),
            error_count=self._to_int(safe_metrics.get("error_count"), default=0),
            total_stage_ms=self._to_float(safe_metrics.get("total_stage_ms"), default=0.0),
            slowest_stage=str(safe_metrics.get("slowest_stage") or ""),
            slowest_stage_ms=self._to_float(safe_metrics.get("slowest_stage_ms"), default=0.0),
            incomplete_stages=self._to_string_list(safe_trace.get("incomplete_stages")),
            emitted_events=emitted_events,
            emitted_summary=emitted_summary,
            source="decision_pipeline",
        )
        return DecisionPipelineTelemetryResult(
            contract=contract,
            metrics=safe_metrics,
            trace=safe_trace,
            warnings=warnings,
        )

    def _collect_metrics(
        self,
        *,
        result: OrchestrationResult,
        warnings: List[str],
    ) -> Dict[str, Any]:
        fallback = self._fallback_metrics(result=result)
        try:
            metrics_raw = self.metrics_builder_factory().summarize(result)
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"telemetry_metrics_failed:{type(exc).__name__}:{exc}")
            return fallback

        if not isinstance(metrics_raw, Mapping):
            if metrics_raw not in (None, "", {}):
                warnings.append("telemetry_metrics_invalid_payload")
            return fallback
        return self._to_mapping(metrics_raw)

    def _collect_trace(
        self,
        *,
        result: OrchestrationResult,
        warnings: List[str],
    ) -> Dict[str, Any]:
        stage_timings = self._extract_stage_timings(result=result)
        stage_order = list(stage_timings.keys())
        context = getattr(result, "context", None)
        events = self._coerce_collection(getattr(context, "events", []))
        try:
            trace_raw = self.trace_builder_factory().build(
                events,
                stage_order=stage_order,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"telemetry_trace_failed:{type(exc).__name__}:{exc}")
            return {
                "stages": [],
                "incomplete_stages": [],
                "missing_stages": stage_order,
                "event_count": len(events),
            }

        if not isinstance(trace_raw, Mapping):
            if trace_raw not in (None, "", {}):
                warnings.append("telemetry_trace_invalid_payload")
            return {
                "stages": [],
                "incomplete_stages": [],
                "missing_stages": stage_order,
                "event_count": len(events),
            }
        return self._to_mapping(trace_raw)

    @staticmethod
    def _check_trace_consistency(
        *,
        metrics: Mapping[str, Any],
        trace: Mapping[str, Any],
        warnings: List[str],
    ) -> None:
        trace_stage_count = len(
            DecisionPipelineTelemetryEngine._coerce_collection(
                DecisionPipelineTelemetryEngine._read_mapping_field(
                    trace,
                    ("stages",),
                    default=[],
                )
            )
        )
        metric_stage_count = DecisionPipelineTelemetryEngine._to_int(
            DecisionPipelineTelemetryEngine._read_mapping_field(metrics, ("stage_count",)),
            default=0,
        )
        if trace_stage_count != metric_stage_count:
            warnings.append(
                "telemetry_trace_stage_mismatch:"
                f"metrics={metric_stage_count},trace={trace_stage_count}"
            )
        missing = DecisionPipelineTelemetryEngine._coerce_collection(
            DecisionPipelineTelemetryEngine._read_mapping_field(
                trace,
                ("missing_stages",),
                default=[],
            )
        )
        if missing:
            warnings.append(
                "telemetry_trace_missing_stages:"
                f"{','.join([str(item) for item in missing])}"
            )

    def _runtime_settings_from_contract(
        self,
        *,
        runtime_config: RuntimeConfigContract,
        warnings: List[str],
    ) -> RuntimeSettings:
        settings = RuntimeSettings(
            app_name=runtime_config.app_name,
            environment=runtime_config.environment,
            orchestrator_strict=runtime_config.orchestrator_strict,
            observability_enabled=runtime_config.observability_enabled,
            observability_emit_events=runtime_config.observability_emit_events,
            observability_emit_summary=runtime_config.observability_emit_summary,
            observability_write_file=runtime_config.observability_write_file,
            observability_stderr=runtime_config.observability_stderr,
            observability_file=runtime_config.observability_file,
            decision_pipeline_enabled=runtime_config.decision_pipeline_enabled,
        )
        normalized, setting_warnings = settings.enforce_invariants()
        for warning in self._coerce_collection(setting_warnings):
            warnings.append(f"telemetry_runtime_config_normalized:{warning}")
        return normalized

    @staticmethod
    def _normalize_runtime_contract(
        runtime_config: Any,
        *,
        warnings: List[str],
    ) -> RuntimeConfigContract:
        if isinstance(runtime_config, RuntimeConfigContract):
            return runtime_config

        runtime_mapping = DecisionPipelineTelemetryEngine._to_mapping(runtime_config)
        if runtime_mapping:
            warnings.append("telemetry_runtime_config_coerced_from_mapping")
            return RuntimeConfigContract(
                app_name=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("app_name",),
                    default="era",
                ),
                environment=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("environment",),
                    default="development",
                ),
                orchestrator_strict=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("orchestrator_strict",),
                    default=False,
                ),
                decision_pipeline_enabled=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("decision_pipeline_enabled",),
                    default=True,
                ),
                observability_enabled=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("observability_enabled",),
                    default=True,
                ),
                observability_emit_events=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("observability_emit_events",),
                    default=False,
                ),
                observability_emit_summary=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("observability_emit_summary",),
                    default=True,
                ),
                observability_write_file=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("observability_write_file",),
                    default=False,
                ),
                observability_stderr=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("observability_stderr",),
                    default=False,
                ),
                observability_file=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("observability_file",),
                    default="logs/orchestration_events.jsonl",
                ),
                source=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("source",),
                    default="environment",
                ),
                overrides_applied=DecisionPipelineTelemetryEngine._read_mapping_field(
                    runtime_mapping,
                    ("overrides_applied",),
                    default=[],
                ),
            )

        warnings.append("telemetry_runtime_config_invalid_type")
        return RuntimeConfigContract()

    def _fallback_metrics(self, *, result: OrchestrationResult) -> Dict[str, Any]:
        timings = self._extract_stage_timings(result=result)
        context = getattr(result, "context", None)
        events = self._coerce_collection(getattr(context, "events", []))
        errors = self._coerce_collection(getattr(context, "errors", []))
        status = str(getattr(getattr(result, "status", ""), "value", getattr(result, "status", "")))
        total_stage_ms = sum(
            self._to_float(item, default=0.0)
            for item in self._coerce_collection(timings.values())
        )
        return {
            "run_id": str(getattr(result, "run_id", "")),
            "status": status,
            "stage_count": len(timings),
            "event_count": len(events),
            "error_count": len(errors),
            "total_stage_ms": total_stage_ms,
            "slowest_stage": "",
            "slowest_stage_ms": 0.0,
            "stage_timings_ms": dict(timings),
        }

    def _extract_stage_timings(self, *, result: OrchestrationResult) -> Dict[str, float]:
        raw = self._to_mapping(getattr(result, "stage_timings_ms", {}))
        if not raw:
            return {}
        normalized: Dict[str, float] = {}
        for key, value in raw.items():
            stage = self._normalize_text(key)
            if not stage:
                continue
            normalized[stage] = self._to_float(value, default=0.0)
        return normalized

    def _build_logger(
        self,
        *,
        runtime_settings: RuntimeSettings,
        warnings: List[str],
    ) -> Any | None:
        try:
            return self.logger_factory(runtime_settings)
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"telemetry_logger_init_failed:{type(exc).__name__}:{exc}")
            return None

    @staticmethod
    def _emit_events(
        *,
        logger: Any,
        result: OrchestrationResult,
        warnings: List[str],
    ) -> int:
        emitted = 0
        context = getattr(result, "context", None)
        events = DecisionPipelineTelemetryEngine._coerce_collection(
            getattr(context, "events", []),
        )
        for index, event in enumerate(events):
            try:
                logger.log_event(event, extra={"pipeline": "decision_pipeline"})
                emitted += 1
            except TypeError as exc:
                try:
                    logger.log_event(event)
                    emitted += 1
                    warnings.append(
                        f"telemetry_emit_event_without_extra:index={index}:{type(exc).__name__}:{exc}"
                    )
                except Exception as fallback_exc:  # pragma: no cover - defensive path
                    warnings.append(
                        "telemetry_emit_event_failed:"
                        f"index={index}:{type(fallback_exc).__name__}:{fallback_exc}"
                    )
            except Exception as exc:  # pragma: no cover - defensive path
                warnings.append(
                    f"telemetry_emit_event_failed:index={index}:{type(exc).__name__}:{exc}"
                )
        return emitted

    @staticmethod
    def _emit_summary(
        *,
        logger: Any,
        result: OrchestrationResult,
        runtime_config: RuntimeConfigContract,
        metrics: Mapping[str, Any],
        trace: Mapping[str, Any],
        metadata: Mapping[str, Any],
        warnings: List[str],
    ) -> bool:
        run_metadata = {
            "pipeline": "decision_pipeline",
            "runtime_config_source": runtime_config.source,
            "runtime_overrides": DecisionPipelineTelemetryEngine._coerce_collection(
                runtime_config.overrides_applied
            ),
        }
        if metadata:
            run_metadata["metadata"] = DecisionPipelineTelemetryEngine._to_mapping(metadata)

        try:
            logger.log_summary(
                run_id=result.run_id,
                status=str(getattr(result.status, "value", result.status)),
                metrics=DecisionPipelineTelemetryEngine._to_mapping(metrics),
                trace=DecisionPipelineTelemetryEngine._to_mapping(trace),
                metadata=run_metadata,
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"telemetry_emit_summary_failed:{type(exc).__name__}:{exc}")
            return False

    def _sanitize_metadata(
        self,
        *,
        metadata: Mapping[str, Any] | None,
        warnings: List[str],
    ) -> Dict[str, Any]:
        if metadata is None:
            return {}
        normalized_metadata = self._to_mapping(metadata)
        if not normalized_metadata:
            warnings.append("telemetry_metadata_invalid_type")
            return {}

        sanitized = self._sanitize_payload(
            self._to_mapping(normalized_metadata),
            path="metadata",
            warnings=warnings,
            max_depth=self.sanitize_max_depth,
            max_items=self.sanitize_max_items,
            max_string=self.sanitize_max_string,
        )
        return self._ensure_mapping(sanitized, name="metadata", warnings=warnings)

    @staticmethod
    def _ensure_mapping(value: Any, *, name: str, warnings: List[str]) -> Dict[str, Any]:
        mapping = DecisionPipelineTelemetryEngine._to_mapping(value)
        if mapping:
            return mapping
        warnings.append(f"telemetry_sanitized:{name}:coerced_to_empty_mapping")
        return {}

    def _sanitize_payload(
        self,
        value: Any,
        *,
        path: str,
        warnings: List[str],
        max_depth: int = 6,
        max_items: int = 200,
        max_string: int = 4000,
    ) -> Any:
        if max_depth <= 0:
            warnings.append(f"telemetry_sanitized:{path}:max_depth_reached")
            return "<max_depth_reached>"

        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                warnings.append(f"telemetry_sanitized:{path}:non_finite_float")
                return 0.0
            return value
        if isinstance(value, (bytes, bytearray)):
            warnings.append(f"telemetry_sanitized:{path}:bytes_decoded")
            return bytes(value).decode("utf-8", errors="replace")
        if isinstance(value, str):
            if len(value) <= max_string:
                return value
            warnings.append(f"telemetry_sanitized:{path}:string_truncated")
            return value[:max_string]
        if isinstance(value, Mapping):
            sanitized: Dict[str, Any] = {}
            try:
                raw_items = value.items()
            except Exception:
                warnings.append(f"telemetry_sanitized:{path}:mapping_coerced_to_empty")
                return sanitized
            items, _ = self._coerce_iterable_items(raw_items, preserve_partial=True)
            if len(items) > max_items:
                warnings.append(f"telemetry_sanitized:{path}:mapping_truncated")
            for key, item_value in items[:max_items]:
                item_key = str(key)
                if item_key in sanitized:
                    warnings.append(
                        f"telemetry_sanitized:{path}:duplicate_key_after_stringify:{item_key}"
                    )
                    continue
                sanitized[item_key] = self._sanitize_payload(
                    item_value,
                    path=f"{path}.{item_key}",
                    warnings=warnings,
                    max_depth=max_depth - 1,
                    max_items=max_items,
                    max_string=max_string,
                )
            return sanitized
        if isinstance(value, (list, tuple, set)):
            values = self._coerce_collection(value)
            if isinstance(value, set):
                values = sorted(values, key=lambda item: str(item))
            if len(values) > max_items:
                warnings.append(f"telemetry_sanitized:{path}:sequence_truncated")
            return [
                self._sanitize_payload(
                    item,
                    path=f"{path}[{index}]",
                    warnings=warnings,
                    max_depth=max_depth - 1,
                    max_items=max_items,
                    max_string=max_string,
                )
                for index, item in enumerate(values[:max_items])
            ]

        warnings.append(f"telemetry_sanitized:{path}:coerced_to_string")
        return str(value)

    @staticmethod
    def _to_int(value: Any, *, default: int) -> int:
        if value is None:
            return default
        try:
            numeric = int(value)
        except Exception:
            return default
        return numeric if numeric >= 0 else 0

    @staticmethod
    def _to_float(value: Any, *, default: float) -> float:
        if value is None:
            return default
        try:
            numeric = float(value)
        except Exception:
            return default
        if not math.isfinite(numeric):
            return default
        return numeric

    @staticmethod
    def _coerce_collection(value: Any) -> List[Any]:
        if value in (None, ""):
            return []
        if isinstance(value, (str, bytes, bytearray)):
            return []
        if isinstance(value, Mapping):
            return []
        if isinstance(value, Sequence):
            items, _ = DecisionPipelineTelemetryEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            return items
        if isinstance(value, Iterable):
            items, _ = DecisionPipelineTelemetryEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            return items
        return []

    @staticmethod
    def _to_string_list(value: Any) -> List[str]:
        items = DecisionPipelineTelemetryEngine._coerce_collection(value)
        normalized: List[str] = []
        seen = set()
        for item in items:
            text = DecisionPipelineTelemetryEngine._normalize_text(item)
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        if isinstance(value, Mapping):
            try:
                raw_items = value.items()
            except Exception:
                return {}
            items, _ = DecisionPipelineTelemetryEngine._coerce_iterable_items(
                raw_items,
                preserve_partial=True,
            )
            normalized: Dict[str, Any] = {}
            for key, item in items:
                text = DecisionPipelineTelemetryEngine._normalize_text(key)
                if text:
                    normalized[text] = item
            return normalized
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items, failed = DecisionPipelineTelemetryEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not raw_items:
                return {}
            normalized: Dict[str, Any] = {}
            for raw_item in raw_items:
                try:
                    key, item = raw_item
                except Exception:
                    return {}
                text = DecisionPipelineTelemetryEngine._normalize_text(key)
                if text:
                    normalized[text] = item
            return normalized
        return {}

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            DecisionPipelineTelemetryEngine._normalize_text(value)
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
            DecisionPipelineTelemetryEngine._normalize_key_name(key)
            for key in keys
        }
        try:
            raw_items = source.items()
        except Exception:
            return default
        items, _ = DecisionPipelineTelemetryEngine._coerce_iterable_items(
            raw_items,
            preserve_partial=True,
        )
        for raw_key, value in items:
            if DecisionPipelineTelemetryEngine._normalize_key_name(raw_key) in normalized_targets:
                return value
        return default

    @staticmethod
    def _dedupe_warnings(warnings: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            deduped.append(warning)
        return deduped
