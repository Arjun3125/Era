"""Run-level metrics derivation from orchestration results."""

from __future__ import annotations

from collections.abc import Iterable
import math
from typing import Any, Dict, Mapping, Sequence

from ..orchestrator.runtime import OrchestrationResult


class OrchestrationMetrics:
    """Computes normalized run metrics for reporting and telemetry sinks."""

    def summarize(self, result: OrchestrationResult) -> Dict[str, Any]:
        timings = self._normalize_timings(getattr(result, "stage_timings_ms", {}))

        total_stage_ms = round(sum(float(v) for v in timings.values()), 3)
        total_runtime_ms = round(
            self._to_non_negative_float(
                getattr(result, "total_runtime_ms", total_stage_ms),
                default=total_stage_ms,
            ),
            3,
        )
        overhead_ms = round(max(0.0, total_runtime_ms - total_stage_ms), 3)
        max_stage = ""
        max_stage_ms = 0.0
        if timings:
            max_stage, max_stage_ms = max(
                timings.items(),
                key=lambda item: float(item[1]),
            )
            max_stage_ms = round(float(max_stage_ms), 3)

        context = getattr(result, "context", None)
        status = getattr(getattr(result, "status", None), "value", getattr(result, "status", "unknown"))
        events = self._coerce_sequence(getattr(context, "events", []))
        errors = self._coerce_sequence(getattr(context, "errors", []))

        return {
            "run_id": self._normalize_text(getattr(result, "run_id", "")),
            "status": self._normalize_text(status, default="unknown"),
            "stage_count": len(timings),
            "event_count": len(events),
            "error_count": len(errors),
            "total_stage_ms": total_stage_ms,
            "total_runtime_ms": total_runtime_ms,
            "runtime_overhead_ms": overhead_ms,
            "slowest_stage": max_stage,
            "slowest_stage_ms": max_stage_ms,
            "stage_timings_ms": dict(timings),
        }

    @staticmethod
    def _normalize_timings(value: Any) -> Dict[str, float]:
        mapping = OrchestrationMetrics._to_mapping(value)
        if not mapping:
            return {}

        normalized: Dict[str, float] = {}
        for raw_name, raw_timing in mapping.items():
            stage_name = OrchestrationMetrics._normalize_text(raw_name)
            if not stage_name:
                continue
            normalized[stage_name] = round(
                OrchestrationMetrics._to_non_negative_float(raw_timing, default=0.0),
                3,
            )
        return normalized

    @staticmethod
    def _coerce_sequence(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray)):
            if isinstance(value, str) and not value.strip():
                return []
            return []
        if isinstance(value, Mapping):
            return []
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            return list(value)
        if isinstance(value, Iterable):
            return OrchestrationMetrics._coerce_iterable_items(value, preserve_partial=True) or []
        return []

    @staticmethod
    def _to_non_negative_float(value: Any, *, default: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return default
        if not math.isfinite(numeric):
            return default
        if numeric < 0.0:
            return 0.0
        return numeric

    @staticmethod
    def _normalize_text(value: Any, *, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        return text or default

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        items = OrchestrationMetrics._coerce_mapping_items(value)
        if items is None:
            return {}
        normalized: Dict[str, Any] = {}
        for raw_key, item in items:
            key = OrchestrationMetrics._normalize_text(raw_key)
            if not key:
                continue
            normalized[key] = item
        return normalized

    @staticmethod
    def _coerce_mapping_items(value: Any) -> list[tuple[Any, Any]] | None:
        if isinstance(value, Mapping):
            raw_items = OrchestrationMetrics._coerce_iterable_items(value.items(), preserve_partial=True)
            if raw_items is None:
                return []
            items: list[tuple[Any, Any]] = []
            for raw_item in raw_items:
                try:
                    key, item_value = raw_item
                except Exception:
                    return []
                items.append((key, item_value))
            return items
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items = OrchestrationMetrics._coerce_iterable_items(value, preserve_partial=True)
            if raw_items is None:
                return None
            items: list[tuple[Any, Any]] = []
            for raw_item in raw_items:
                try:
                    key, item_value = raw_item
                except Exception:
                    return None
                items.append((key, item_value))
            return items
        return None

    @staticmethod
    def _coerce_iterable_items(value: Any, *, preserve_partial: bool = False) -> list[Any] | None:
        try:
            iterator = iter(value)
        except Exception:
            return []
        items: list[Any] = []
        while True:
            try:
                item = next(iterator)
            except StopIteration:
                return items
            except Exception:
                if preserve_partial and items:
                    return items
                return None
            items.append(item)
