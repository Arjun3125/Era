"""Observability primitives for orchestrated execution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from config import RuntimeSettings, resolve_runtime_settings
from .logger import StructuredEventLogger
from .metrics import OrchestrationMetrics
from .tracing import EventTraceBuilder


def create_metrics_builder() -> OrchestrationMetrics:
    """Create a metrics summarizer for orchestration results."""
    return OrchestrationMetrics()


def create_trace_builder() -> EventTraceBuilder:
    """Create a trace builder for orchestration event streams."""
    return EventTraceBuilder()


def _coerce_iterable_items(
    value: Any,
    *,
    preserve_partial: bool,
) -> tuple[list[Any], bool]:
    try:
        iterator = iter(value)
    except Exception:
        return [], True
    items: list[Any] = []
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


def _coerce_override_mapping(settings: Any) -> dict[Any, Any]:
    if isinstance(settings, Mapping):
        raw_items, failed = _coerce_iterable_items(settings.items(), preserve_partial=True)
        if failed and not raw_items:
            raise TypeError("settings mapping could not be read.")
        overrides: dict[Any, Any] = {}
        for raw_item in raw_items:
            try:
                key, value = raw_item
            except Exception as exc:
                raise TypeError("settings iterable must contain key-value pairs.") from exc
            try:
                overrides[key] = value
            except Exception as exc:
                raise TypeError("settings iterable keys must be hashable.") from exc
        return overrides
    if isinstance(settings, Iterable) and not isinstance(settings, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(settings, preserve_partial=True)
        if failed and not raw_items:
            raise TypeError("settings iterable must contain key-value pairs.")
        overrides: dict[Any, Any] = {}
        for raw_item in raw_items:
            try:
                key, value = raw_item
            except Exception as exc:
                raise TypeError("settings iterable must contain key-value pairs.") from exc
            try:
                overrides[key] = value
            except Exception as exc:
                raise TypeError("settings iterable keys must be hashable.") from exc
        return overrides
    raise TypeError("settings must be RuntimeSettings, mapping, or iterable key-value pairs.")


def _coerce_runtime_settings(settings: RuntimeSettings | Any) -> RuntimeSettings:
    if isinstance(settings, RuntimeSettings):
        return settings
    overrides = _coerce_override_mapping(settings)
    resolved, _ = resolve_runtime_settings(overrides, strict=False)
    return resolved


def create_structured_logger(settings: RuntimeSettings | Any) -> StructuredEventLogger:
    """Create a structured observability logger from runtime settings."""
    return StructuredEventLogger(_coerce_runtime_settings(settings))


__all__ = (
    "EventTraceBuilder",
    "OrchestrationMetrics",
    "StructuredEventLogger",
    "create_metrics_builder",
    "create_structured_logger",
    "create_trace_builder",
)
