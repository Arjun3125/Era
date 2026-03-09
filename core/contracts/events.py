"""Event contracts emitted by the pipeline orchestrator."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional
import uuid


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip().lower()
    return str(value).strip().lower()


def _normalize_token(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    normalized = (
        text.replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


class EventType(str, Enum):
    """Known event categories emitted by the orchestration runtime."""

    RUN_STARTED = "run_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    STAGE_DEGRADED = "stage_degraded"
    RUN_COMPLETED = "run_completed"
    RUN_ABORTED = "run_aborted"

    @classmethod
    def coerce(cls, value: Any) -> "EventType":
        if isinstance(value, cls):
            return value
        text = _normalize_token(value)
        aliases = {
            "runstart": cls.RUN_STARTED.value,
            "run_start": cls.RUN_STARTED.value,
            "stage_start": cls.STAGE_STARTED.value,
            "stage_complete": cls.STAGE_COMPLETED.value,
            "stage_done": cls.STAGE_COMPLETED.value,
            "stage_error": cls.STAGE_FAILED.value,
            "run_complete": cls.RUN_COMPLETED.value,
            "run_finish": cls.RUN_COMPLETED.value,
            "run_abort": cls.RUN_ABORTED.value,
        }
        text = aliases.get(text, text)
        try:
            return cls(text)
        except Exception as exc:
            raise ValueError(f"Unsupported event type '{value}'.") from exc


class EventLevel(str, Enum):
    """Severity level for event records."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @classmethod
    def coerce(cls, value: Any) -> "EventLevel":
        if isinstance(value, cls):
            return value
        text = _normalize_token(value)
        if not text:
            return cls.INFO
        aliases = {
            "warn": cls.WARNING.value,
            "warning": cls.WARNING.value,
            "err": cls.ERROR.value,
            "fatal": cls.ERROR.value,
            "information": cls.INFO.value,
        }
        text = aliases.get(text, text)
        try:
            return cls(text)
        except Exception:
            return cls.INFO


@dataclass(frozen=True)
class EventRecord:
    """Immutable event envelope for logs, metrics, and auditing."""

    run_id: str
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    stage: Optional[str] = None
    level: EventLevel = EventLevel.INFO
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        normalized_run_id = self._normalize_required_text(
            self.run_id,
            field_name="EventRecord.run_id",
        )

        normalized_event_type = EventType.coerce(self.event_type)
        normalized_level = EventLevel.coerce(self.level)

        normalized_payload = self._normalize_payload(self.payload)
        stage = self._normalize_optional_text(self.stage)
        event_id = self._normalize_optional_text(self.event_id) or str(uuid.uuid4())
        timestamp = self._normalize_timestamp(self.timestamp)

        object.__setattr__(self, "run_id", normalized_run_id)
        object.__setattr__(self, "event_type", normalized_event_type)
        object.__setattr__(self, "payload", normalized_payload)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "level", normalized_level)
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "timestamp", timestamp)

    @staticmethod
    def _normalize_required_text(value: Any, *, field_name: str) -> str:
        if value is None:
            text = ""
        elif isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        if not text:
            raise ValueError(f"{field_name} must be non-empty.")
        return text

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        if value is None:
            text = ""
        elif isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_payload(value: Any) -> Dict[str, Any]:
        mapping_items = EventRecord._coerce_mapping_items(value)
        if mapping_items is not None:
            normalized: Dict[str, Any] = {}
            for raw_key, raw_value in mapping_items:
                key = EventRecord._normalize_optional_text(raw_key) or ""
                if not key or key in normalized:
                    continue
                normalized[key] = raw_value
            return normalized
        if value is None:
            return {}
        return {"value": value}

    @staticmethod
    def _coerce_mapping_items(value: Any) -> list[tuple[Any, Any]] | None:
        if isinstance(value, Mapping):
            try:
                return list(value.items())
            except Exception:
                return []
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items, failed = EventRecord._coerce_iterable_items(
                value,
                preserve_partial=False,
            )
            if failed:
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

    @staticmethod
    def _normalize_timestamp(value: Any) -> str:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()
        if value is None:
            text = ""
        elif isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        if text:
            return text
        return datetime.now(timezone.utc).isoformat()
