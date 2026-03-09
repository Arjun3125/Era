"""Pluggable module interface for staged orchestration execution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Protocol, Sequence

from .context import ExecutionContext


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _normalize_key_name(value: Any) -> str:
    return (
        _coerce_text(value)
        .lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


def _normalize_token(value: Any) -> str:
    normalized = _normalize_key_name(value)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        items = list(dict(value).items())
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
            return {}
        items = []
        for raw_item in raw_items:
            try:
                key, item_value = raw_item
            except Exception:
                return {}
            items.append((key, item_value))
    else:
        return {}
    normalized: Dict[str, Any] = {}
    for raw_key, item_value in items:
        key = _coerce_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = item_value
    return normalized


def _read_mapping_field(source: Mapping[str, Any], keys: Sequence[str]) -> Any:
    targets = {_normalize_key_name(key) for key in keys}
    for raw_key, raw_value in dict(source).items():
        if _normalize_key_name(raw_key) in targets:
            return raw_value
    return None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        return False
    if isinstance(value, (bytes, bytearray)):
        text = bytes(value).decode("utf-8", errors="replace").strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
        return False
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
        return False
    return False


def _coerce_iterable_items(value: Any, *, preserve_partial: bool) -> tuple[list[Any], bool]:
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


class ModuleStatus(str, Enum):
    """Normalized execution status for module invocations."""

    SUCCESS = "success"
    DEGRADED = "degraded"
    FAILED = "failed"

    @classmethod
    def coerce(cls, value: Any) -> "ModuleStatus":
        if isinstance(value, cls):
            return value
        text = _normalize_token(value)
        aliases = {
            "ok": cls.SUCCESS.value,
            "pass": cls.SUCCESS.value,
            "warning": cls.DEGRADED.value,
            "warn": cls.DEGRADED.value,
            "error": cls.FAILED.value,
        }
        text = aliases.get(text, text)
        try:
            return cls(text)
        except Exception as exc:
            raise ValueError(f"Unsupported module status '{value}'.") from exc


@dataclass
class ModuleHealth:
    """Health probe output exposed by each pluggable module."""

    ok: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.ok = _coerce_bool(self.ok)
        self.details = _coerce_mapping(self.details)


@dataclass
class ModuleResult:
    """Structured output returned by any pipeline module."""

    status: ModuleStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.status = ModuleStatus.coerce(self.status)
        self.outputs = self._to_mapping(self.outputs)
        self.metrics = self._to_mapping(self.metrics)
        self.errors = self._normalize_errors(self.errors)

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        return _coerce_mapping(value)

    @staticmethod
    def _normalize_errors(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
            return [text] if text else []
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, Mapping):
            text = ModuleResult._coerce_error_text(value)
            return [text] if text else []

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            items = list(value)
        elif isinstance(value, Iterable):
            items, failed = _coerce_iterable_items(value, preserve_partial=True)
            if failed and not items:
                text = ModuleResult._coerce_error_text(value)
                return [text] if text else []
        else:
            text = ModuleResult._coerce_error_text(value)
            return [text] if text else []

        errors: list[str] = []
        seen = set()
        for item in items:
            text = ModuleResult._coerce_error_text(item)
            if not text or text in seen:
                continue
            seen.add(text)
            errors.append(text)
        return errors

    @staticmethod
    def _coerce_error_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        if isinstance(value, Mapping):
            for keys in (
                ("message", "error_message", "message_text"),
                ("error", "error_text"),
                ("detail", "details"),
                ("code",),
            ):
                candidate = _read_mapping_field(value, keys)
                text = str(candidate).strip() if candidate is not None else ""
                if text:
                    return text
            return str(dict(value)).strip()
        return str(value).strip()


class ModulePlugin(Protocol):
    """Standard module contract for orchestrator-compatible plugins."""

    def name(self) -> str:
        """Stable plugin identifier."""

    def capabilities(self) -> Mapping[str, Any]:
        """Capability declaration used by planners/routing."""

    def validate(self, context: ExecutionContext) -> None:
        """Raise if preconditions are not satisfied."""

    def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run module logic against current execution context."""

    def health(self) -> ModuleHealth:
        """Return current operational health of this module."""
