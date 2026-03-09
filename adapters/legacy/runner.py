"""Shared runtime bridge for legacy entrypoints with observability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from config.settings import RuntimeSettings, load_runtime_settings
from core.contracts import InputContract
from core.observability import EventTraceBuilder, OrchestrationMetrics, StructuredEventLogger
from core.orchestrator import OrchestrationResult, PipelineOrchestrator

from .entrypoints import LegacyEntrypointPlugin, plugin_stage_handler


@dataclass
class LegacyRunReport:
    """Execution report returned by the legacy run bridge."""

    exit_code: int
    result: OrchestrationResult
    metrics: Dict[str, Any]
    trace: Dict[str, Any]


def run_legacy_entrypoint(
    *,
    plugin: LegacyEntrypointPlugin,
    command_name: str,
    argv: Optional[Sequence[Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    settings: Optional[RuntimeSettings] = None,
) -> LegacyRunReport:
    """Execute a legacy plugin through central orchestration + telemetry pipeline."""
    if not isinstance(plugin, LegacyEntrypointPlugin):
        raise TypeError("plugin must be a LegacyEntrypointPlugin instance.")

    runtime_settings = _resolve_runtime_settings(settings)
    resolved_command_name = _normalize_command_name(command_name)
    resolved_argv = _normalize_argv(argv)
    run_metadata = _normalize_metadata(metadata)
    plugin_name = _normalize_plugin_name(plugin.name())

    orchestrator = PipelineOrchestrator(
        name=f"legacy.{plugin_name}",
        strict=runtime_settings.orchestrator_strict,
    )
    orchestrator.register_stage(
        f"legacy::{plugin_name}",
        plugin_stage_handler(plugin),
        on_error="abort",
    )

    run_metadata.update(
        {
            "entrypoint_plugin": plugin_name,
            "argv": list(resolved_argv),
            "settings": runtime_settings.to_dict(),
        }
    )

    result = orchestrator.run(
        InputContract(
            user_input=resolved_command_name,
            source="cli",
            metadata={"argv": list(resolved_argv)},
        ),
        metadata=run_metadata,
    )

    metrics = OrchestrationMetrics().summarize(result)
    trace = EventTraceBuilder().build(
        result.context.events,
        stage_order=list(result.stage_timings_ms.keys()),
    )

    observability_warnings = _emit_observability(
        runtime_settings=runtime_settings,
        result=result,
        metrics=metrics,
        trace=trace,
        command_name=resolved_command_name,
        plugin_name=plugin_name,
    )
    if observability_warnings:
        metrics["observability_warning_count"] = len(observability_warnings)
        metrics["observability_warnings"] = list(observability_warnings)
        trace["observability_warnings"] = list(observability_warnings)

    exit_code = _resolve_exit_code(result)

    return LegacyRunReport(
        exit_code=exit_code,
        result=result,
        metrics=metrics,
        trace=trace,
    )


def _resolve_runtime_settings(settings: Optional[RuntimeSettings]) -> RuntimeSettings:
    if settings is None:
        return load_runtime_settings()
    if not isinstance(settings, RuntimeSettings):
        raise TypeError("settings must be RuntimeSettings when provided.")
    return settings


def _normalize_plugin_name(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError("Legacy entrypoint plugin name must be non-empty.")
    return text


def _normalize_command_name(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError("command_name must be non-empty.")
    return text


def _normalize_argv(argv: Any) -> List[str]:
    if argv is None:
        return []
    if isinstance(argv, str):
        return [argv]
    if isinstance(argv, (bytes, bytearray)):
        return [_stringify_argv_item(argv)]
    if isinstance(argv, Mapping):
        raise TypeError("argv must be a sequence of values when provided.")
    if not isinstance(argv, Sequence):
        if hasattr(argv, "__iter__"):
            try:
                return [_stringify_argv_item(item) for item in list(argv)]
            except Exception:
                raise TypeError("argv must be a sequence of values when provided.")
        raise TypeError("argv must be a sequence of values when provided.")
    return [_stringify_argv_item(item) for item in list(argv)]


def _stringify_argv_item(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def _normalize_metadata(metadata: Any) -> Dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, Mapping):
        return {_normalize_mapping_key(key): value for key, value in dict(metadata).items()}
    if hasattr(metadata, "__iter__") and not isinstance(metadata, (str, bytes, bytearray)):
        try:
            pairs = list(metadata)
        except Exception:
            raise TypeError("metadata must be a mapping when provided.")
        normalized: Dict[str, Any] = {}
        for item in pairs:
            if isinstance(item, Mapping):
                raise TypeError("metadata must be a mapping when provided.")
            try:
                key, value = item
            except Exception:
                raise TypeError("metadata must be a mapping when provided.")
            normalized[_normalize_mapping_key(key)] = value
        return normalized
    raise TypeError("metadata must be a mapping when provided.")


def _normalize_mapping_key(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def _emit_observability(
    *,
    runtime_settings: RuntimeSettings,
    result: OrchestrationResult,
    metrics: Dict[str, Any],
    trace: Dict[str, Any],
    command_name: str,
    plugin_name: str,
) -> List[str]:
    if not runtime_settings.observability_enabled:
        return []

    warnings: List[str] = []
    logger: StructuredEventLogger | None = None
    try:
        logger = StructuredEventLogger(runtime_settings)
    except Exception as exc:
        warnings.append(f"observability_logger_init_failed:{type(exc).__name__}:{exc}")
        return warnings

    if runtime_settings.observability_emit_events:
        events = _coerce_event_sequence(getattr(getattr(result, "context", None), "events", None))
        for index, event in enumerate(events):
            try:
                logger.log_event(event)
            except Exception as exc:
                warnings.append(
                    f"observability_event_emit_failed:index={index}:{type(exc).__name__}:{exc}"
                )

    if runtime_settings.observability_emit_summary:
        try:
            logger.log_summary(
                run_id=result.run_id,
                status=result.status.value,
                metrics=metrics,
                trace=trace,
                metadata={"command_name": command_name, "entrypoint": plugin_name},
            )
        except Exception as exc:
            warnings.append(f"observability_summary_emit_failed:{type(exc).__name__}:{exc}")

    return warnings


def _coerce_event_sequence(value: Any) -> List[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, (str, bytes, bytearray)):
        return []
    if isinstance(value, Sequence):
        return list(value)
    if hasattr(value, "__iter__"):
        try:
            return list(value)
        except Exception:
            return []
    return [value]


def _resolve_exit_code(result: OrchestrationResult) -> int:
    context = getattr(result, "context", None)
    state = getattr(context, "state", {}) if context is not None else {}
    state_mapping = state if isinstance(state, Mapping) else {}
    exit_code = _coerce_exit_code(state_mapping.get("legacy_exit_code"), default=0)
    status = str(getattr(result.status, "value", result.status)).strip().lower()
    if status == "aborted" and exit_code == 0:
        return 1
    return exit_code


def _coerce_exit_code(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(text)
    except Exception:
        return default
