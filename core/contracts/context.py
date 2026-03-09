"""Shared runtime context passed between pipeline stages."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence
import uuid

from .events import EventLevel, EventRecord, EventType
from .io import ErrorContract, InputContract


@dataclass
class ExecutionContext:
    """Mutable state bag for a single orchestration run."""

    input_contract: InputContract
    config: Dict[str, Any] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    events: List[EventRecord] = field(default_factory=list)
    errors: List[ErrorContract] = field(default_factory=list)
    current_stage: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.input_contract, InputContract):
            raise TypeError("ExecutionContext.input_contract must be InputContract.")

        self.config = self._to_mapping(self.config, name="config")
        self.metadata = self._to_mapping(self.metadata, name="metadata")
        self.state = self._to_mapping(self.state, name="state")

        self.run_id = self._normalize_required_text(self.run_id) or str(uuid.uuid4())
        self.started_at = self._normalize_started_at(self.started_at)
        self.current_stage = self._normalize_optional_text(self.current_stage)

        self.events = self._normalize_events(self.events)
        self.errors = self._normalize_errors(self.errors)

    def emit(
        self,
        event_type: EventType | str,
        *,
        payload: Optional[Any] = None,
        stage: Optional[str] = None,
        level: EventLevel | str = EventLevel.INFO,
    ) -> EventRecord:
        """Append and return an event record for this run."""
        resolved_event_type = self._normalize_event_type(event_type)
        resolved_level = self._normalize_event_level(level)
        payload_mapping = self._to_mapping_if_possible(payload)
        if payload is None:
            event_payload = {}
        elif payload_mapping is not None:
            event_payload = payload_mapping
        else:
            event_payload = {"value": payload}
        resolved_stage = self._normalize_optional_text(stage or self.current_stage or "")

        event = EventRecord(
            run_id=self.run_id,
            event_type=resolved_event_type,
            payload=event_payload,
            stage=resolved_stage,
            level=resolved_level,
        )
        self.events.append(event)
        return event

    def add_error(
        self,
        error: ErrorContract | Mapping[str, Any] | str | bytes | bytearray,
    ) -> None:
        """Track stage/run level failures for audit and diagnostics."""
        normalized = self._coerce_error(error)
        self.errors.append(normalized)

    @staticmethod
    def _normalize_event_type(event_type: EventType | str) -> EventType:
        if isinstance(event_type, EventType):
            return event_type
        return EventType.coerce(event_type)

    @staticmethod
    def _normalize_event_level(level: EventLevel | str) -> EventLevel:
        if isinstance(level, EventLevel):
            return level
        return EventLevel.coerce(level)

    @staticmethod
    def _to_mapping(value: Any, *, name: str) -> Dict[str, Any]:
        if value is None:
            return {}
        items = ExecutionContext._coerce_mapping_items(value, name=name)
        normalized: Dict[str, Any] = {}
        for raw_key, item in items:
            key = ExecutionContext._normalize_required_text(raw_key)
            if not key or key in normalized:
                continue
            normalized[key] = item
        return normalized

    @staticmethod
    def _to_mapping_if_possible(value: Any) -> Dict[str, Any] | None:
        if value is None:
            return {}
        try:
            return ExecutionContext._to_mapping(value, name="payload")
        except TypeError:
            return None

    @staticmethod
    def _coerce_mapping_items(value: Any, *, name: str) -> List[tuple[Any, Any]]:
        if isinstance(value, Mapping):
            try:
                return list(dict(value).items())
            except Exception as exc:
                raise TypeError(f"ExecutionContext.{name} must be a mapping.") from exc
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items = ExecutionContext._coerce_iterable_items(
                value,
                error_message=f"ExecutionContext.{name} must be a mapping.",
            )
            pairs: List[tuple[Any, Any]] = []
            for raw_item in raw_items:
                try:
                    key, item_value = raw_item
                except Exception as exc:
                    raise TypeError(f"ExecutionContext.{name} must be a mapping.") from exc
                pairs.append((key, item_value))
            return pairs
        raise TypeError(f"ExecutionContext.{name} must be a mapping.")

    @staticmethod
    def _normalize_events(value: Any) -> List[EventRecord]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray)):
            raise TypeError("ExecutionContext.events must be a sequence of EventRecord.")
        if isinstance(value, Sequence):
            items = list(value)
        elif isinstance(value, Iterable):
            items = ExecutionContext._coerce_iterable_items(
                value,
                error_message="ExecutionContext.events must be a sequence of EventRecord.",
            )
        else:
            raise TypeError("ExecutionContext.events must be a sequence of EventRecord.")
        normalized: List[EventRecord] = []
        for item in items:
            if isinstance(item, EventRecord):
                normalized.append(item)
                continue
            raise TypeError("ExecutionContext.events must contain only EventRecord values.")
        return normalized

    @staticmethod
    def _normalize_errors(value: Any) -> List[ErrorContract]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray)):
            raise TypeError("ExecutionContext.errors must be a sequence.")
        if isinstance(value, Sequence):
            items = list(value)
        elif isinstance(value, Iterable):
            items = ExecutionContext._coerce_iterable_items(
                value,
                error_message="ExecutionContext.errors must be a sequence.",
            )
        else:
            raise TypeError("ExecutionContext.errors must be a sequence.")
        normalized: List[ErrorContract] = []
        for item in items:
            normalized.append(ExecutionContext._coerce_error(item))
        return normalized

    @staticmethod
    def _coerce_iterable_items(value: Any, *, error_message: str) -> List[Any]:
        try:
            iterator = iter(value)
        except Exception as exc:
            raise TypeError(error_message) from exc
        items: List[Any] = []
        while True:
            try:
                item = next(iterator)
            except StopIteration:
                break
            except Exception as exc:
                raise TypeError(error_message) from exc
            items.append(item)
        return items

    @staticmethod
    def _coerce_error(
        value: ErrorContract | Mapping[str, Any] | str | bytes | bytearray,
    ) -> ErrorContract:
        if isinstance(value, ErrorContract):
            return value
        if isinstance(value, Mapping):
            details_raw = ExecutionContext._read_mapping_field(value, ("details",), default={})
            try:
                details = ExecutionContext._to_mapping(details_raw, name="error_details")
            except TypeError:
                details = {}
            code = ExecutionContext._normalize_required_text(
                ExecutionContext._read_mapping_field(value, ("code",))
            )
            message = ExecutionContext._normalize_required_text(
                ExecutionContext._read_mapping_field(value, ("message", "error", "detail"))
            )
            return ErrorContract(
                code=code or "runtime_error",
                message=message or "unspecified_error",
                stage=ExecutionContext._normalize_optional_text(
                    ExecutionContext._read_mapping_field(value, ("stage",), default="")
                ),
                recoverable=ExecutionContext._coerce_bool(
                    ExecutionContext._read_mapping_field(
                        value,
                        ("recoverable",),
                        default=False,
                    )
                ),
                details=details,
            )
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip() or "unspecified_error"
            return ErrorContract(code="runtime_error", message=text, recoverable=False)
        if isinstance(value, str):
            text = value.strip() or "unspecified_error"
            return ErrorContract(code="runtime_error", message=text, recoverable=False)
        raise TypeError(
            "ExecutionContext errors must be ErrorContract, mapping, string, or bytes."
        )

    @staticmethod
    def _coerce_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return False
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off"}:
                return False
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off"}:
                return False
        return False

    @staticmethod
    def _normalize_required_text(value: Any) -> str:
        if value is None:
            text = ""
        elif isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        return text

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        text = ExecutionContext._normalize_required_text(value)
        return text or None

    @staticmethod
    def _normalize_started_at(value: Any) -> str:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()
        text = ExecutionContext._normalize_required_text(value)
        return text or datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            ExecutionContext._normalize_required_text(value)
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
        normalized_keys = {ExecutionContext._normalize_key_name(key) for key in keys}
        for raw_key, value in dict(source).items():
            if ExecutionContext._normalize_key_name(raw_key) in normalized_keys:
                return value
        return default
