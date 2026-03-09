"""Tests for legacy entrypoint plugin adapter and stage wrapper."""

from __future__ import annotations

import pytest

from adapters.legacy.entrypoints import LegacyEntrypointPlugin, plugin_stage_handler
from core.contracts import ExecutionContext, InputContract, ModuleResult, ModuleStatus


def _context() -> ExecutionContext:
    return ExecutionContext(input_contract=InputContract(user_input="x"))


def test_plugin_init_normalizes_name_args_and_kwargs():
    plugin = LegacyEntrypointPlugin(
        plugin_name=" legacy.example ",
        entrypoint=lambda *_args, **_kwargs: None,
        args=[1, 2],
        kwargs={1: "x"},
    )
    assert plugin.name() == "legacy.example"
    assert plugin.args == (1, 2)
    assert plugin.kwargs == {"1": "x"}


def test_plugin_init_accepts_iterable_args_and_kwargs_pairs():
    plugin = LegacyEntrypointPlugin(
        plugin_name="legacy.iterable",
        entrypoint=lambda *_args, **_kwargs: None,
        args=(item for item in [1, 2, 3]),
        kwargs=[("a", 1), (b"b", 2)],
    )
    assert plugin.args == (1, 2, 3)
    assert plugin.kwargs == {"a": 1, "b": 2}


def test_plugin_init_validates_name_args_and_kwargs():
    with pytest.raises(ValueError, match="plugin name must be non-empty"):
        LegacyEntrypointPlugin(plugin_name=" ", entrypoint=lambda: None)
    with pytest.raises(TypeError, match="args must be a sequence"):
        LegacyEntrypointPlugin(plugin_name="p", entrypoint=lambda: None, args=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="kwargs must be a mapping"):
        LegacyEntrypointPlugin(plugin_name="p", entrypoint=lambda: None, kwargs=1)  # type: ignore[arg-type]


def test_plugin_validate_requires_execution_context_and_callable():
    plugin = LegacyEntrypointPlugin(plugin_name="p", entrypoint=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ExecutionContext"):
        plugin.validate(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="not callable"):
        plugin.validate(_context())


def test_plugin_execute_normalizes_system_exit_codes():
    plugin = LegacyEntrypointPlugin(
        plugin_name="p",
        entrypoint=lambda: (_ for _ in ()).throw(SystemExit("2")),
    )
    result = plugin.execute(_context())
    assert result.status == ModuleStatus.FAILED
    assert result.outputs["legacy_exit_code"] == 2
    assert result.errors == ["SystemExit(2)"]


def test_plugin_execute_exception_returns_failed_result_with_exit_code():
    plugin = LegacyEntrypointPlugin(
        plugin_name="p",
        entrypoint=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    result = plugin.execute(_context())
    assert result.status == ModuleStatus.FAILED
    assert result.outputs["legacy_exit_code"] == 1
    assert any("RuntimeError: boom" in item for item in result.errors)


def test_plugin_stage_handler_treats_success_with_errors_as_degraded():
    class _NoisyPlugin:
        def validate(self, _context):
            return None

        def execute(self, _context):
            return ModuleResult(
                status=ModuleStatus.SUCCESS,
                outputs={"ok": True},
                errors=["warning"],
            )

    outcome = plugin_stage_handler(_NoisyPlugin())(_context())  # type: ignore[arg-type]
    assert outcome.degraded is True
    assert outcome.continue_pipeline is True
    assert outcome.outputs["ok"] is True
    assert outcome.errors == ["warning"]


def test_plugin_stage_handler_rejects_invalid_plugins_and_results():
    with pytest.raises(TypeError, match="callable 'validate"):
        plugin_stage_handler(object())  # type: ignore[arg-type]

    class _BadPlugin:
        def validate(self, _context):
            return None

        def execute(self, _context):
            return {"not": "module_result"}

    handler = plugin_stage_handler(_BadPlugin())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must return ModuleResult"):
        handler(_context())
