"""Tests for config package public API surface."""

from __future__ import annotations

import pytest

from config import (
    RUNTIME_SETTING_FIELDS,
    RUNTIME_SETTING_NAMES,
    RuntimeSettings,
    resolve_runtime_settings,
)


def test_runtime_setting_names_match_fields():
    assert tuple(sorted(RUNTIME_SETTING_FIELDS.keys())) == RUNTIME_SETTING_NAMES


def test_resolve_runtime_settings_returns_settings_and_warnings():
    settings, warnings = resolve_runtime_settings({"unknown_key": 1})
    assert isinstance(settings, RuntimeSettings)
    assert any("Unknown runtime setting" in item for item in warnings)


def test_resolve_runtime_settings_strict_mode_raises_on_invalid_override():
    with pytest.raises(ValueError, match="Unknown runtime setting"):
        resolve_runtime_settings({"unknown_key": 1}, strict=True)


def test_resolve_runtime_settings_accepts_boolean_like_strict_values():
    settings, warnings = resolve_runtime_settings({"unknown_key": 1}, strict="false")  # type: ignore[arg-type]
    assert isinstance(settings, RuntimeSettings)
    assert any("Unknown runtime setting" in item for item in warnings)

    settings_bytes, warnings_bytes = resolve_runtime_settings({"unknown_key": 1}, strict=b"0")  # type: ignore[arg-type]
    assert isinstance(settings_bytes, RuntimeSettings)
    assert any("Unknown runtime setting" in item for item in warnings_bytes)

    with pytest.raises(TypeError, match="strict must be a boolean"):
        resolve_runtime_settings({}, strict=2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="strict must be a boolean"):
        resolve_runtime_settings({}, strict="maybe")  # type: ignore[arg-type]


def test_resolve_runtime_settings_normalizes_warning_values(monkeypatch):
    def _fake_loader(_overrides, *, strict):
        _ = strict
        return RuntimeSettings(), [" ok ", b"warn-bytes", "", None]

    monkeypatch.setattr("config.load_runtime_settings_report", _fake_loader)
    _, warnings = resolve_runtime_settings({}, strict=False)
    assert warnings == ["ok", "warn-bytes"]
