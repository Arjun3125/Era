"""Tests for central runtime configuration settings helpers."""

from __future__ import annotations

import pytest

from config.settings import (
    RuntimeSettings,
    canonicalize_runtime_key,
    load_runtime_settings_report,
    normalize_runtime_overrides,
)


_RUNTIME_ENV_KEYS = (
    "ERA_APP_NAME",
    "ERA_ENV",
    "ERA_ORCH_STRICT",
    "ERA_OBS_ENABLED",
    "ERA_OBS_EMIT_EVENTS",
    "ERA_OBS_EMIT_SUMMARY",
    "ERA_OBS_WRITE_FILE",
    "ERA_OBS_STDERR",
    "ERA_OBS_FILE",
    "ERA_DECISION_PIPELINE_ENABLED",
)


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch):
    for key in _RUNTIME_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_canonicalize_runtime_key_supports_extra_normalization_and_prefixes():
    assert canonicalize_runtime_key("Observability Emit Events") == "observability_emit_events"
    assert canonicalize_runtime_key("era-runtime-observability-file") == "observability_file"
    assert canonicalize_runtime_key(" era.runtime.decision-pipeline-enabled ") == "decision_pipeline_enabled"


def test_normalize_runtime_overrides_validates_mapping_and_bool_int_values():
    with pytest.raises(TypeError, match="mapping"):
        normalize_runtime_overrides(["bad"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="mapping"):
        normalize_runtime_overrides([])  # type: ignore[arg-type]

    normalized, warnings = normalize_runtime_overrides(
        {
            "obs_enabled": 1,
            "obs_emit_events": 2,  # invalid int bool
            "not_real": True,
        }
    )
    assert normalized["observability_enabled"] is True
    assert "observability_emit_events" not in normalized
    assert any("Invalid boolean for runtime setting 'observability_emit_events' ignored." in item for item in warnings)
    assert any("Unknown runtime setting 'not_real' ignored." in item for item in warnings)


def test_normalize_runtime_overrides_supports_bytes_keys_and_values():
    normalized, warnings = normalize_runtime_overrides(
        {
            b"obs_enabled": b"0",
            b"OBS_FILE": b"logs/runtime.jsonl",
        }
    )
    assert normalized["observability_enabled"] is False
    assert normalized["observability_file"] == "logs/runtime.jsonl"
    assert warnings == []


def test_normalize_runtime_overrides_coerces_strict_strings():
    normalized, warnings = normalize_runtime_overrides(
        {"unknown_key": True},
        strict="false",  # type: ignore[arg-type]
    )
    assert normalized == {}
    assert any("Unknown runtime setting" in item for item in warnings)

    with pytest.raises(TypeError, match="strict must be a boolean"):
        normalize_runtime_overrides({"obs_enabled": True}, strict="maybe")  # type: ignore[arg-type]


def test_runtime_settings_enforce_invariants_coerces_booleans_and_disables_observability_children():
    settings = RuntimeSettings(
        app_name="",
        environment="",
        orchestrator_strict="1",  # type: ignore[arg-type]
        observability_enabled="false",  # type: ignore[arg-type]
        observability_emit_events="true",  # type: ignore[arg-type]
        observability_emit_summary="true",  # type: ignore[arg-type]
        observability_write_file="true",  # type: ignore[arg-type]
        observability_stderr="true",  # type: ignore[arg-type]
        decision_pipeline_enabled="1",  # type: ignore[arg-type]
        observability_file="",
    )

    normalized, warnings = settings.enforce_invariants()
    assert normalized.app_name == "era"
    assert normalized.environment == "development"
    assert normalized.orchestrator_strict is True
    assert normalized.observability_enabled is False
    assert normalized.observability_emit_events is False
    assert normalized.observability_emit_summary is False
    assert normalized.observability_write_file is False
    assert normalized.observability_stderr is False
    assert normalized.decision_pipeline_enabled is True
    assert any("defaulted to 'era'" in item for item in warnings)
    assert any("disabled because observability_enabled is false" in item for item in warnings)


def test_load_runtime_settings_report_rejects_non_mapping_overrides():
    with pytest.raises(TypeError, match="mapping"):
        load_runtime_settings_report(overrides=["bad"])  # type: ignore[arg-type]


def test_load_runtime_settings_report_rejects_invalid_strict_flag():
    with pytest.raises(TypeError, match="strict must be a boolean"):
        load_runtime_settings_report(strict="maybe")  # type: ignore[arg-type]
