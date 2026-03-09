"""Event-to-trace transformation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from ..contracts.events import EventType


@dataclass
class StageTrace:
    """Trace summary for one pipeline stage."""

    stage: str
    started_at: str = ""
    completed_at: str = ""
    status: str = "unknown"
    event_count: int = 0
    last_event_type: str = ""


class EventTraceBuilder:
    """Builds stage-level traces from orchestrator event history."""

    def build(
        self,
        events: Sequence[Any],
        *,
        stage_order: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        stages: Dict[str, StageTrace] = {}
        ordered_names: List[str] = []
        normalized_stage_order = self._coerce_stage_order(stage_order)
        normalized_events = self._coerce_events(events)

        for stage_name in normalized_stage_order:
            name = self._normalize_text(stage_name)
            if not name or name in ordered_names:
                continue
            ordered_names.append(name)

        for event in normalized_events:
            stage = self._normalize_text(self._event_value(event, "stage", "stage_name"))
            if not stage:
                continue
            trace = stages.setdefault(stage, StageTrace(stage=stage))
            if stage not in ordered_names:
                ordered_names.append(stage)

            trace.event_count += 1
            trace.last_event_type = self._event_type_value(event)
            timestamp = self._normalize_text(
                self._event_value(event, "timestamp", "time", "occurred_at", "created_at")
            )

            if trace.status == "unknown" and timestamp:
                trace.started_at = timestamp

            event_type = self._event_type(event)
            if event_type == EventType.STAGE_STARTED:
                if not trace.started_at:
                    trace.started_at = timestamp
                trace.status = "running"
            elif event_type == EventType.STAGE_COMPLETED:
                if trace.status not in {"failed", "degraded"}:
                    trace.status = "completed"
                trace.completed_at = timestamp
            elif event_type == EventType.STAGE_DEGRADED:
                if trace.status != "failed":
                    trace.status = "degraded"
                trace.completed_at = timestamp
            elif event_type == EventType.STAGE_FAILED:
                trace.status = "failed"
                trace.completed_at = timestamp

        ordered = [asdict(stages[name]) for name in ordered_names if name in stages]
        missing_stages = [name for name in ordered_names if name not in stages]
        return {
            "stages": ordered,
            "incomplete_stages": [
                item["stage"] for item in ordered if item.get("status") == "running"
            ],
            "missing_stages": missing_stages,
            "event_count": len(normalized_events),
        }

    @staticmethod
    def _event_type(event: Any) -> EventType | None:
        raw = EventTraceBuilder._event_value(
            event,
            "event_type",
            "event",
            "type",
            "name",
        )
        if isinstance(raw, EventType):
            return raw
        try:
            return EventType.coerce(raw)
        except Exception:
            return None

    @staticmethod
    def _event_type_value(event: Any) -> str:
        event_type = EventTraceBuilder._event_type(event)
        if event_type is not None:
            return event_type.value
        return EventTraceBuilder._normalize_text(
            EventTraceBuilder._event_value(event, "event_type", "event", "type", "name")
        )

    @staticmethod
    def _event_value(event: Any, *names: str) -> Any:
        for name in names:
            value = getattr(event, name, None)
            if value is not None:
                return value
        if isinstance(event, Mapping):
            return EventTraceBuilder._mapping_value(event, *names)
        return None

    @staticmethod
    def _mapping_value(mapping: Mapping[Any, Any], *names: str) -> Any:
        for name in names:
            if name in mapping:
                return mapping[name]

        normalized_targets = set()
        for name in names:
            normalized = EventTraceBuilder._normalize_key_text(name)
            if normalized:
                normalized_targets.add(normalized)
        if not normalized_targets:
            return None

        mapping_items = EventTraceBuilder._coerce_iterable_items(
            mapping.items(),
            preserve_partial=True,
        )
        if mapping_items is None:
            return None
        for item in mapping_items:
            try:
                raw_key, raw_value = item
            except Exception:
                continue
            normalized_key = EventTraceBuilder._normalize_key_text(raw_key)
            if normalized_key and normalized_key in normalized_targets:
                return raw_value
        return None

    @staticmethod
    def _coerce_stage_order(value: Optional[Sequence[str]]) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray)):
            if isinstance(value, str) and not value.strip():
                return []
            return []
        if isinstance(value, Mapping):
            return []
        if isinstance(value, Sequence):
            raw_items = EventTraceBuilder._coerce_iterable_items(value, preserve_partial=True)
            if raw_items is None:
                return []
            return [EventTraceBuilder._normalize_text(item) for item in raw_items]
        if isinstance(value, Iterable):
            raw_items = EventTraceBuilder._coerce_iterable_items(value, preserve_partial=True)
            if raw_items is None:
                return []
            return [
                EventTraceBuilder._normalize_text(item)
                for item in raw_items
            ]
        return []

    @staticmethod
    def _coerce_events(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray)):
            if isinstance(value, str) and not value.strip():
                return []
            return []
        if isinstance(value, Mapping):
            return [value]
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            raw_items = EventTraceBuilder._coerce_iterable_items(value, preserve_partial=True)
            return raw_items or []
        if isinstance(value, Iterable):
            return EventTraceBuilder._coerce_iterable_items(value, preserve_partial=True) or []
        return [value]

    @staticmethod
    def _coerce_iterable_items(
        value: Any,
        *,
        preserve_partial: bool = False,
    ) -> List[Any] | None:
        try:
            iterator = iter(value)
        except Exception:
            return None
        items: List[Any] = []
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

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_text(value: Any) -> str:
        text = EventTraceBuilder._normalize_text(value)
        if not text:
            return ""
        return (
            text.lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )
