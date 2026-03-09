"""Central runtime configuration package."""

from __future__ import annotations

from typing import Any, Mapping

from .settings import (
    RUNTIME_SETTING_FIELDS,
    RuntimeSettings,
    canonicalize_runtime_key,
    load_runtime_settings,
    load_runtime_settings_report,
    normalize_runtime_overrides,
)

RUNTIME_SETTING_NAMES = tuple(sorted(RUNTIME_SETTING_FIELDS.keys()))
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _coerce_strict_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise TypeError("strict must be a boolean.")
    text = _normalize_text(value).lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise TypeError("strict must be a boolean.")


def resolve_runtime_settings(
    overrides: Mapping[str, Any] | None = None,
    *,
    strict: Any = False,
) -> tuple[RuntimeSettings, list[str]]:
    """Load normalized runtime settings together with warning diagnostics."""
    strict_enabled = _coerce_strict_flag(strict)
    settings, warnings = load_runtime_settings_report(overrides, strict=strict_enabled)
    normalized_warnings = []
    for item in warnings:
        text = _normalize_text(item)
        if text:
            normalized_warnings.append(text)
    return settings, normalized_warnings


__all__ = (
    "RUNTIME_SETTING_FIELDS",
    "RUNTIME_SETTING_NAMES",
    "RuntimeSettings",
    "canonicalize_runtime_key",
    "load_runtime_settings",
    "load_runtime_settings_report",
    "normalize_runtime_overrides",
    "resolve_runtime_settings",
)
