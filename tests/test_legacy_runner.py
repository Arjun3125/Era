"""Tests for legacy entrypoint runner orchestration bridge."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from adapters.legacy.entrypoints import LegacyEntrypointPlugin
from adapters.legacy import runner
from config.settings import RuntimeSettings


def _settings_for_tests(**overrides):
    base = RuntimeSettings(
        observability_enabled=False,
        observability_emit_events=False,
        observability_emit_summary=False,
        observability_stderr=False,
        observability_write_file=False,
    )
    payload = base.to_dict()
    payload.update(overrides)
    return RuntimeSettings(**payload)


def test_run_legacy_entrypoint_validates_inputs():
    plugin = LegacyEntrypointPlugin(plugin_name="legacy.test", entrypoint=lambda: None)

    with pytest.raises(TypeError, match="LegacyEntrypointPlugin"):
        runner.run_legacy_entrypoint(  # type: ignore[arg-type]
            plugin=object(),
            command_name="cmd",
        )

    with pytest.raises(ValueError, match="command_name must be non-empty"):
        runner.run_legacy_entrypoint(
            plugin=plugin,
            command_name="  ",
        )

    with pytest.raises(TypeError, match="metadata must be a mapping"):
        runner.run_legacy_entrypoint(
            plugin=plugin,
            command_name="cmd",
            metadata=["bad"],  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="settings must be RuntimeSettings"):
        runner.run_legacy_entrypoint(
            plugin=plugin,
            command_name="cmd",
            settings={"x": 1},  # type: ignore[arg-type]
        )


def test_run_legacy_entrypoint_resilient_to_observability_failures(monkeypatch):
    class _FlakyLogger:
        def __init__(self, _settings):
            self.event_calls = 0

        def log_event(self, _event):
            self.event_calls += 1
            raise RuntimeError("event boom")

        def log_summary(self, **_kwargs):
            raise RuntimeError("summary boom")

    monkeypatch.setattr(runner, "StructuredEventLogger", _FlakyLogger)

    plugin = LegacyEntrypointPlugin(plugin_name="legacy.test", entrypoint=lambda: {"ok": True})
    report = runner.run_legacy_entrypoint(
        plugin=plugin,
        command_name="legacy.test",
        settings=_settings_for_tests(
            observability_enabled=True,
            observability_emit_events=True,
            observability_emit_summary=True,
        ),
    )

    assert report.exit_code == 0
    assert report.metrics["observability_warning_count"] >= 2
    warnings = report.metrics["observability_warnings"]
    assert any(item.startswith("observability_event_emit_failed:") for item in warnings)
    assert any(item.startswith("observability_summary_emit_failed:") for item in warnings)
    assert report.trace["observability_warnings"] == warnings


def test_run_legacy_entrypoint_aborted_without_exit_code_defaults_to_one():
    plugin = LegacyEntrypointPlugin(plugin_name="legacy.bad", entrypoint=None)  # type: ignore[arg-type]
    report = runner.run_legacy_entrypoint(
        plugin=plugin,
        command_name="legacy.bad",
        settings=_settings_for_tests(),
    )

    assert report.result.status.value == "aborted"
    assert report.exit_code == 1


def test_run_legacy_entrypoint_normalizes_argv_and_plugin_name():
    plugin = LegacyEntrypointPlugin(plugin_name="legacy.argv", entrypoint=lambda: None)
    report = runner.run_legacy_entrypoint(
        plugin=plugin,
        command_name="legacy.argv",
        argv="--help",  # type: ignore[arg-type]
        settings=_settings_for_tests(),
    )
    assert report.result.context.metadata["argv"] == ["--help"]
    assert report.result.context.metadata["entrypoint_plugin"] == "legacy.argv"

    with pytest.raises(ValueError, match="plugin name must be non-empty"):
        runner.run_legacy_entrypoint(
            plugin=LegacyEntrypointPlugin(plugin_name="  ", entrypoint=lambda: None),
            command_name="legacy.badname",
            settings=_settings_for_tests(),
        )


def test_normalize_argv_decodes_byte_values():
    assert runner._normalize_argv(b"--help") == ["--help"]
    assert runner._normalize_argv([b"--json", bytearray(b"--yaml"), 7]) == [
        "--json",
        "--yaml",
        "7",
    ]


def test_normalize_argv_accepts_iterable_non_sequence_inputs():
    argv_iter = (item for item in [b"--alpha", "--beta", 3])
    assert runner._normalize_argv(argv_iter) == ["--alpha", "--beta", "3"]


def test_emit_observability_ignores_string_event_collections(monkeypatch):
    captured: list[object] = []

    class _Logger:
        def __init__(self, _settings):
            pass

        def log_event(self, event):
            captured.append(event)

        def log_summary(self, **_kwargs):
            pass

    monkeypatch.setattr(runner, "StructuredEventLogger", _Logger)

    fake_result = SimpleNamespace(
        context=SimpleNamespace(events="not-events"),
        run_id="run-1",
        status=SimpleNamespace(value="completed"),
    )
    warnings = runner._emit_observability(
        runtime_settings=_settings_for_tests(
            observability_enabled=True,
            observability_emit_events=True,
            observability_emit_summary=False,
        ),
        result=fake_result,  # type: ignore[arg-type]
        metrics={},
        trace={},
        command_name="legacy.test",
        plugin_name="legacy.test",
    )

    assert warnings == []
    assert captured == []


def test_normalize_metadata_accepts_iterable_key_value_pairs():
    metadata_iter = (item for item in [("a", 1), (b"b", 2)])
    assert runner._normalize_metadata(metadata_iter) == {"a": 1, "b": 2}


def test_emit_observability_supports_iterable_event_collections(monkeypatch):
    captured: list[object] = []

    class _Logger:
        def __init__(self, _settings):
            pass

        def log_event(self, event):
            captured.append(event)

        def log_summary(self, **_kwargs):
            pass

    monkeypatch.setattr(runner, "StructuredEventLogger", _Logger)

    fake_result = SimpleNamespace(
        context=SimpleNamespace(events=(item for item in [{"id": 1}, {"id": 2}])),
        run_id="run-1",
        status=SimpleNamespace(value="completed"),
    )
    warnings = runner._emit_observability(
        runtime_settings=_settings_for_tests(
            observability_enabled=True,
            observability_emit_events=True,
            observability_emit_summary=False,
        ),
        result=fake_result,  # type: ignore[arg-type]
        metrics={},
        trace={},
        command_name="legacy.test",
        plugin_name="legacy.test",
    )

    assert warnings == []
    assert captured == [{"id": 1}, {"id": 2}]
