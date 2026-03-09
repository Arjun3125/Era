"""Tests for the runtime configuration resolution engine."""

from __future__ import annotations

from collections.abc import Mapping
import pytest

from core.contracts import ExecutionContext, InputContract, RuntimeConfigContract
from modules.runtime_config.engine import RuntimeConfigEngine
from modules.runtime_config.module import RuntimeConfigModule


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


class _FaultyOverrideMapping(Mapping):
    def __getitem__(self, key):
        data = {
            "environment": "iter-env",
            "obs_enabled": "0",
        }
        return data[key]

    def __iter__(self):
        yield "environment"
        yield "obs_enabled"
        raise RuntimeError("override-iter-failed")

    def __len__(self):
        return 2

    def items(self):
        yield ("environment", "iter-env")
        yield ("obs_enabled", "0")
        raise RuntimeError("override-items-failed")


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch):
    for key in _RUNTIME_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_runtime_override_precedence_and_trace():
    engine = RuntimeConfigEngine()

    result = engine.resolve(
        context_config={
            "runtime_settings": {
                "environment": "context",
                "obs_enabled": True,
            }
        },
        input_metadata={
            "runtime_config": {
                "environment": "input",
                "obs_enabled": False,
            }
        },
        metadata={
            "runtime_config": {
                "environment": "run",
                "obs_emit_events": True,
            }
        },
    )

    assert result.contract.environment == "run"
    assert result.contract.observability_enabled is False
    assert result.contract.observability_emit_events is False

    assert "environment" in result.contract.overrides_applied
    assert "observability_enabled" in result.contract.overrides_applied
    assert "observability_emit_events" in result.contract.overrides_applied

    override_sources = result.settings_dict.get("override_sources", [])
    assert "context.config.runtime_settings:environment" in override_sources
    assert "input.metadata.runtime_config:environment" in override_sources
    assert "run.metadata.runtime_config:environment" in override_sources

    warnings_blob = "\n".join(result.warnings)
    assert "runtime setting 'environment' overrides value" in warnings_blob
    assert "observability_emit_events disabled because observability_enabled is false" in warnings_blob


def test_runtime_nested_settings_override_supported():
    engine = RuntimeConfigEngine()

    result = engine.resolve(
        metadata={
            "runtime": {
                "settings": {
                    "obs_enabled": "0",
                    "obs_stderr": "1",
                }
            }
        }
    )

    assert result.contract.observability_enabled is False
    assert result.contract.observability_stderr is False
    assert "observability_enabled" in result.contract.overrides_applied
    assert "observability_stderr" in result.contract.overrides_applied


def test_runtime_strict_mode_rejects_invalid_override():
    engine = RuntimeConfigEngine()

    with pytest.raises(ValueError, match="Unknown runtime setting"):
        engine.resolve(
            metadata={
                "runtime_overrides_strict": True,
                "runtime_config": {
                    "not_a_real_setting": True,
                },
            }
        )


def test_runtime_invalid_strict_toggle_warns_but_does_not_abort():
    engine = RuntimeConfigEngine()

    result = engine.resolve(
        metadata={
            "runtime_overrides_strict": "maybe",
            "runtime_config": {
                "obs_enabled": "false",
            },
        }
    )

    assert result.contract.observability_enabled is False
    assert result.settings_dict.get("runtime_overrides_strict") is False
    warnings_blob = "\n".join(result.warnings)
    assert "invalid boolean for runtime strict-overrides ignored" in warnings_blob


def test_runtime_invalid_strict_int_toggle_warns_and_remains_non_strict():
    engine = RuntimeConfigEngine()

    result = engine.resolve(
        metadata={
            "runtime_overrides_strict": 2,
            "runtime_config": {
                "obs_enabled": "false",
            },
        }
    )

    assert result.contract.observability_enabled is False
    assert result.settings_dict.get("runtime_overrides_strict") is False
    warnings_blob = "\n".join(result.warnings)
    assert "invalid boolean for runtime strict-overrides ignored" in warnings_blob


def test_runtime_strict_control_keys_inside_override_maps_do_not_raise():
    engine = RuntimeConfigEngine()

    result = engine.resolve(
        metadata={
            "runtime_overrides_strict": True,
            "runtime_config": {
                "runtime_overrides_strict": True,
                "obs_enabled": "false",
            },
            "runtime": {
                "settings": {
                    "strict_runtime_overrides": True,
                    "obs_emit_summary": "0",
                }
            },
        }
    )

    assert result.settings_dict.get("runtime_overrides_strict") is True
    assert result.contract.observability_enabled is False
    assert result.contract.observability_emit_summary is False
    assert "observability_enabled" in result.contract.overrides_applied
    assert "observability_emit_summary" in result.contract.overrides_applied


def test_runtime_engine_accepts_normalized_and_bytes_override_container_keys():
    engine = RuntimeConfigEngine()

    result = engine.resolve(
        metadata={
            b"runtime-config": {
                b"obs_enabled": b"0",
                b"obs_emit_events": b"1",
            },
            "Runtime": {
                "Settings": {
                    "obs_stderr": "1",
                }
            },
            b"runtime_overrides_strict": b"0",
        }
    )

    assert result.settings_dict.get("runtime_overrides_strict") is False
    assert result.contract.observability_enabled is False
    assert result.contract.observability_emit_events is False
    assert result.contract.observability_stderr is False
    override_sources = result.settings_dict.get("override_sources", [])
    assert "run.metadata.runtime_config:observability_enabled" in override_sources
    assert "run.metadata.runtime.settings:observability_stderr" in override_sources


def test_runtime_engine_accepts_iterable_override_payload_and_container_strict_flag():
    engine = RuntimeConfigEngine()

    with pytest.raises(ValueError, match="Unknown runtime setting"):
        engine.resolve(
            metadata={
                "runtime_config": [
                    ("runtime_overrides_strict", "1"),
                    ("obs_enabled", "false"),
                    ("not_a_real_setting", True),
                ]
            }
        )


def test_runtime_engine_ignores_iterable_payload_items_that_are_mappings():
    engine = RuntimeConfigEngine()
    result = engine.resolve(
        metadata={
            "runtime_config": [{"environment": "prod", "obs_enabled": "0"}],
        }
    )

    assert result.contract.environment == "development"
    assert result.contract.observability_enabled is True
    assert result.contract.overrides_applied == []


def test_runtime_engine_preserves_partial_override_mapping_items():
    engine = RuntimeConfigEngine()
    result = engine.resolve(
        metadata={
            "runtime_config": _FaultyOverrideMapping(),
        }
    )

    assert result.contract.environment == "iter-env"
    assert result.contract.observability_enabled is False
    assert "environment" in result.contract.overrides_applied
    assert "observability_enabled" in result.contract.overrides_applied


class _MalformedRuntimeEngine:
    def resolve(self, **kwargs):
        return {
            "settings_dict": "bad-settings",
            "contract": "bad-contract",
            "warnings": "legacy-warning",
        }


class _ExplodingRuntimeEngine:
    def resolve(self, **kwargs):
        raise RuntimeError("runtime boom")


class _PartialIterable:
    def __init__(self, *items):
        self._items = items

    def __iter__(self):
        for item in self._items:
            yield item
        raise RuntimeError("iter-failed")


class _PartialPayloadMapping(dict):
    def items(self):
        def _items():
            yield ("settings-dict", [("app_name", "iter-app"), ("obs_enabled", "0")])
            yield ("warnings", _PartialIterable("warn_a", "warn_b"))
            raise RuntimeError("items-failed")

        return _items()


def test_runtime_module_normalizes_malformed_engine_payload():
    module = RuntimeConfigModule(engine=_MalformedRuntimeEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))

    result = module.execute(context)

    assert result.status.value == "degraded"
    assert isinstance(result.outputs["runtime_config_contract"], RuntimeConfigContract)
    assert result.outputs["runtime_settings"]["app_name"] == "era"
    assert "legacy-warning" in result.outputs["runtime_config_warnings"]


def test_runtime_module_degrades_on_engine_exception():
    module = RuntimeConfigModule(engine=_ExplodingRuntimeEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))

    result = module.execute(context)

    assert result.status.value == "degraded"
    assert result.outputs["runtime_settings"] == {}
    assert result.outputs["runtime_config_contract"].source == "runtime_config.module.exception"
    assert any("RuntimeError" in err for err in result.errors)


def test_runtime_module_preserves_scalar_contract_values_and_iterable_warnings():
    class _ScalarRuntimeEngine:
        def resolve(self, **kwargs):
            return {
                "settings_dict": {
                    "app_name": 0,
                    "environment": 0,
                    "observability_file": 0,
                    "source": 0,
                    1: "x",
                    "overrides_applied": (item for item in ["obs_enabled", "obs_enabled"]),
                },
                "contract": {},
                "warnings": (item for item in [b" warn ", "warn", ""]),
            }

    module = RuntimeConfigModule(engine=_ScalarRuntimeEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    result = module.execute(context)

    contract = result.outputs["runtime_config_contract"]
    assert contract.app_name == "0"
    assert contract.environment == "0"
    assert contract.observability_file == "0"
    assert contract.source == "0"
    assert contract.overrides_applied == ["obs_enabled"]
    assert result.outputs["runtime_settings"]["1"] == "x"
    assert "warn" in result.outputs["runtime_config_warnings"]


def test_runtime_module_normalizes_iterable_resolution_payloads_and_alias_contract_keys():
    class _IterableRuntimeEngine:
        def resolve(self, **kwargs):
            return {
                "settings-dict": [
                    (b"app_name", "iter-app"),
                    ("environment", "prod"),
                    ("obs_enabled", "0"),
                    ("overrides_applied", ["obs_enabled", "obs_enabled"]),
                ],
                "contract": [
                    ("obs_emit_summary", "0"),
                    ("source", "iterable-source"),
                ],
                "warnings": [b" warn ", "warn", ""],
            }

    module = RuntimeConfigModule(engine=_IterableRuntimeEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    result = module.execute(context)

    contract = result.outputs["runtime_config_contract"]
    assert contract.observability_emit_summary is False
    assert contract.source == "iterable-source"
    assert result.outputs["runtime_settings"]["app_name"] == "iter-app"
    assert result.outputs["runtime_settings"]["environment"] == "prod"
    assert "warn" in result.outputs["runtime_config_warnings"]


def test_runtime_module_accepts_json_mapping_resolution_payloads():
    class _JsonRuntimeEngine:
        def resolve(self, **kwargs):
            return {
                "settings_dict": '{"app_name":"json-app","environment":"prod","obs_enabled":"0"}',
                "contract": '{"source":"json-source","obs_emit_summary":"0"}',
                "warnings": "json-warn",
            }

    module = RuntimeConfigModule(engine=_JsonRuntimeEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    result = module.execute(context)

    contract = result.outputs["runtime_config_contract"]
    assert contract.source == "json-source"
    assert contract.observability_emit_summary is False
    assert result.outputs["runtime_settings"]["app_name"] == "json-app"
    assert result.outputs["runtime_settings"]["environment"] == "prod"
    assert "json-warn" in result.outputs["runtime_config_warnings"]


def test_runtime_module_preserves_partial_resolution_payload_items():
    class _PartialRuntimeEngine:
        def resolve(self, **kwargs):
            return _PartialPayloadMapping()

    module = RuntimeConfigModule(engine=_PartialRuntimeEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    result = module.execute(context)

    contract = result.outputs["runtime_config_contract"]
    assert result.outputs["runtime_settings"]["app_name"] == "iter-app"
    assert contract.app_name == "iter-app"
    assert contract.observability_enabled is False
    assert result.outputs["runtime_config_warnings"] == ["warn_a", "warn_b"]
