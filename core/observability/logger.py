"""Structured event logger for orchestration telemetry."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional

from config.settings import RuntimeSettings
from ..contracts.events import EventRecord


class StructuredEventLogger:
    """Emits JSONL records to stderr and/or file targets."""

    def __init__(
        self,
        settings: RuntimeSettings,
        *,
        sanitize_max_depth: int = 6,
        sanitize_max_items: int = 200,
        sanitize_max_string: int = 4000,
    ):
        normalized, _ = settings.enforce_invariants()
        self.settings = normalized
        self.file_path = Path(normalized.observability_file)
        self.sanitize_max_depth = max(int(sanitize_max_depth), 1)
        self.sanitize_max_items = max(int(sanitize_max_items), 1)
        self.sanitize_max_string = max(int(sanitize_max_string), 1)

    def log_event(self, event: EventRecord, *, extra: Optional[Dict[str, Any]] = None) -> None:
        event_type = getattr(getattr(event, "event_type", None), "value", getattr(event, "event_type", ""))
        level = getattr(getattr(event, "level", None), "value", getattr(event, "level", "info"))
        payload = getattr(event, "payload", {})
        payload_value = self._to_mapping(payload)
        if not payload_value:
            payload_value = {"value": payload}

        record: Dict[str, Any] = {
            "kind": "orchestration_event",
            "app": self.settings.app_name,
            "environment": self.settings.environment,
            "timestamp": self._normalize_text(
                getattr(event, "timestamp", None),
                default=datetime.now(timezone.utc).isoformat(),
            ),
            "run_id": self._normalize_text(getattr(event, "run_id", None)),
            "event_id": self._normalize_text(getattr(event, "event_id", None)),
            "event_type": self._normalize_text(event_type, default="unknown"),
            "stage": self._normalize_optional_text(getattr(event, "stage", None)),
            "payload": payload_value,
            "level": self._normalize_text(level, default="info").lower(),
        }
        extra_mapping = self._to_mapping(extra)
        if extra_mapping:
            record.update(extra_mapping)
        elif extra is not None:
            record["extra"] = {"value": extra}
        self._emit_record(record)

    def log_summary(
        self,
        *,
        run_id: str,
        status: str,
        metrics: Dict[str, Any],
        trace: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        metrics_payload = self._to_mapping(metrics)
        trace_payload = self._to_mapping(trace)
        metadata_payload = self._to_mapping(metadata)
        record = {
            "kind": "orchestration_summary",
            "app": self.settings.app_name,
            "environment": self.settings.environment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "status": status,
            "metrics": metrics_payload,
            "trace": trace_payload,
            "metadata": metadata_payload,
        }
        self._emit_record(record)

    def _emit_record(self, record: Dict[str, Any]) -> None:
        if not self.settings.observability_stderr and not self.settings.observability_write_file:
            return

        sanitized = self._sanitize_mapping(
            record,
            max_depth=self.sanitize_max_depth,
            max_mapping_items=max(self.sanitize_max_items, len(record)),
            max_sequence_items=self.sanitize_max_items,
            max_string=self.sanitize_max_string,
        )
        line = json.dumps(sanitized, default=str)
        failures: list[str] = []

        if self.settings.observability_stderr:
            try:
                print(line, file=sys.stderr, flush=True)
            except Exception as exc:
                failures.append(f"stderr:{type(exc).__name__}:{exc}")
        if self.settings.observability_write_file:
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with self.file_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as exc:
                failures.append(f"file:{type(exc).__name__}:{exc}")

        if failures:
            raise OSError("; ".join(failures))

    def _sanitize_mapping(
        self,
        value: Any,
        *,
        max_depth: int = 6,
        max_mapping_items: int = 200,
        max_sequence_items: int = 200,
        max_string: int = 4000,
    ) -> Dict[str, Any]:
        mapping = self._to_mapping(value)
        if not mapping:
            return {}
        sanitized: Dict[str, Any] = {}
        item_count = 0
        for raw_key, raw_value in mapping.items():
            if item_count >= max_mapping_items:
                break
            item_count += 1
            key = self._normalize_text(raw_key)
            if not key:
                continue
            if key in sanitized:
                continue
            sanitized[key] = self._sanitize_value(
                raw_value,
                max_depth=max_depth - 1,
                max_mapping_items=max_mapping_items,
                max_sequence_items=max_sequence_items,
                max_string=max_string,
            )
        return sanitized

    def _sanitize_value(
        self,
        value: Any,
        *,
        max_depth: int,
        max_mapping_items: int,
        max_sequence_items: int,
        max_string: int,
    ) -> Any:
        if max_depth <= 0:
            return "<max_depth_reached>"
        if value is None or isinstance(value, (bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                return 0.0
            return value
        if isinstance(value, str):
            if len(value) <= max_string:
                return value
            return value[:max_string]
        if isinstance(value, (bytes, bytearray)):
            decoded = bytes(value).decode("utf-8", errors="replace")
            if len(decoded) <= max_string:
                return decoded
            return decoded[:max_string]
        if isinstance(value, Mapping):
            return self._sanitize_mapping(
                value,
                max_depth=max_depth,
                max_mapping_items=max_mapping_items,
                max_sequence_items=max_sequence_items,
                max_string=max_string,
            )
        if isinstance(value, (list, tuple, set)):
            values = list(value)
            if isinstance(value, set):
                values = sorted(values, key=lambda item: str(item))
            return [
                self._sanitize_value(
                    item,
                    max_depth=max_depth - 1,
                    max_mapping_items=max_mapping_items,
                    max_sequence_items=max_sequence_items,
                    max_string=max_string,
                )
                for item in values[:max_sequence_items]
            ]
        if isinstance(value, Iterable):
            values = self._coerce_sequence_items(value, max_items=max_sequence_items)
            if values is None:
                return str(value)
            return [
                self._sanitize_value(
                    item,
                    max_depth=max_depth - 1,
                    max_mapping_items=max_mapping_items,
                    max_sequence_items=max_sequence_items,
                    max_string=max_string,
                )
                for item in values
            ]
        return str(value)

    @staticmethod
    def _normalize_text(value: Any, *, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        return text or default

    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        text = cls._normalize_text(value)
        return text or None

    @classmethod
    def _to_mapping(cls, value: Any) -> Dict[str, Any]:
        items = cls._coerce_mapping_items(value)
        if items is None:
            return {}
        normalized: Dict[str, Any] = {}
        for raw_key, item in items:
            key = cls._normalize_text(raw_key)
            if not key:
                continue
            normalized[key] = item
        return normalized

    @staticmethod
    def _coerce_mapping_items(value: Any) -> list[tuple[Any, Any]] | None:
        if isinstance(value, Mapping):
            items = StructuredEventLogger._coerce_sequence_items(value.items(), preserve_partial=True)
            if items is None:
                return []
            normalized_items: list[tuple[Any, Any]] = []
            for raw_item in items:
                try:
                    key, item_value = raw_item
                except Exception:
                    return []
                normalized_items.append((key, item_value))
            return normalized_items
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items = StructuredEventLogger._coerce_sequence_items(value, preserve_partial=True)
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
    def _coerce_sequence_items(
        value: Any,
        *,
        max_items: int | None = None,
        preserve_partial: bool = False,
    ) -> list[Any] | None:
        try:
            iterator = iter(value)
        except Exception:
            return None
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
            if max_items is not None and len(items) >= max_items:
                return items
