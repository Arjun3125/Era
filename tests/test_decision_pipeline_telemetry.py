"""Tests for decision pipeline telemetry collection and emission."""

from __future__ import annotations

from dataclasses import dataclass

from core.contracts import EventType, ExecutionContext, InputContract, RuntimeConfigContract
from core.orchestrator.runtime import OrchestrationResult, RunStatus
from modules.decision_pipeline.telemetry import DecisionPipelineTelemetryEngine


def _build_result() -> OrchestrationResult:
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.emit(EventType.STAGE_STARTED, stage="s1")
    context.emit(EventType.STAGE_COMPLETED, stage="s1")
    context.emit(EventType.STAGE_STARTED, stage="s2")
    context.emit(EventType.STAGE_COMPLETED, stage="s2")
    return OrchestrationResult(
        run_id=context.run_id,
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={"s1": 1.25, "s2": 2.5},
        total_runtime_ms=4.0,
    )


class _PartialFailingMapping(dict):
    def items(self):
        def _items():
            yield ("status", "completed")
            yield ("stage_count", "2")
            raise RuntimeError("items boom")

        return _items()


def test_telemetry_collect_without_observability_does_not_emit():
    result = _build_result()
    called = {"logger": 0}

    def _logger_factory(_settings):
        called["logger"] += 1
        raise RuntimeError("logger should not be constructed")

    engine = DecisionPipelineTelemetryEngine(logger_factory=_logger_factory)
    runtime = RuntimeConfigContract(
        observability_enabled=False,
        observability_emit_events=True,
        observability_emit_summary=True,
    )
    telemetry = engine.collect(result=result, runtime_config=runtime, metadata={"k": "v"})

    assert telemetry.contract.emitted_events == 0
    assert telemetry.contract.emitted_summary is False
    assert called["logger"] == 0


@dataclass
class _MetricsStub:
    payload: dict

    def summarize(self, _result):
        return dict(self.payload)


@dataclass
class _TraceStub:
    payload: dict

    def build(self, _events, *, stage_order=None):
        return dict(self.payload)


def test_telemetry_collect_sanitizes_payloads_and_emits_warnings():
    result = _build_result()
    metrics_payload = {
        "status": "completed",
        "stage_count": "3",
        "event_count": float("inf"),
        "error_count": -1,
        "total_stage_ms": float("nan"),
        "slowest_stage": "x" * 40,
        "slowest_stage_ms": "bad",
        "dup": {1: "a", "1": "b"},
    }
    trace_payload = {
        "stages": [{"stage": "s1", "status": "completed"}],
        "incomplete_stages": {"s2", "s1"},
        "missing_stages": ["s2"],
        "event_count": 2,
    }

    engine = DecisionPipelineTelemetryEngine(
        metrics_builder_factory=lambda: _MetricsStub(metrics_payload),
        trace_builder_factory=lambda: _TraceStub(trace_payload),
        sanitize_max_string=8,
    )
    runtime = RuntimeConfigContract(observability_enabled=False)
    telemetry = engine.collect(result=result, runtime_config=runtime, metadata=["bad"])

    assert telemetry.contract.stage_count == 3
    assert telemetry.contract.event_count == 0
    assert telemetry.contract.error_count == 0
    assert telemetry.contract.total_stage_ms == 0.0
    assert telemetry.contract.slowest_stage == "xxxxxxxx"
    assert telemetry.contract.slowest_stage_ms == 0.0
    assert sorted(telemetry.contract.incomplete_stages) == ["s1", "s2"]

    warnings = telemetry.warnings
    assert any(item.startswith("telemetry_trace_stage_mismatch:") for item in warnings)
    assert any(item.startswith("telemetry_trace_missing_stages:") for item in warnings)
    assert any(item == "telemetry_metadata_invalid_type" for item in warnings)
    assert any(item.startswith("telemetry_sanitized:metrics.event_count:non_finite_float") for item in warnings)
    assert any(item.startswith("telemetry_sanitized:metrics.total_stage_ms:non_finite_float") for item in warnings)
    assert any(item.startswith("telemetry_sanitized:metrics.slowest_stage:string_truncated") for item in warnings)
    assert any(item.startswith("telemetry_sanitized:metrics.dup:duplicate_key_after_stringify:1") for item in warnings)


class _FlakyLogger:
    def __init__(self, _settings):
        self.event_calls = 0
        self.summary_calls = 0

    def log_event(self, _event, *, extra=None):
        self.event_calls += 1
        if self.event_calls == 1:
            raise RuntimeError("event fail")

    def log_summary(self, **kwargs):
        self.summary_calls += 1
        raise RuntimeError("summary fail")


def test_telemetry_collect_handles_event_and_summary_emit_failures_independently():
    result = _build_result()
    holder = {"logger": None}

    def _factory(settings):
        logger = _FlakyLogger(settings)
        holder["logger"] = logger
        return logger

    engine = DecisionPipelineTelemetryEngine(logger_factory=_factory)
    runtime = RuntimeConfigContract(
        observability_enabled=True,
        observability_emit_events=True,
        observability_emit_summary=True,
        app_name="",
        environment="",
        observability_write_file=True,
        observability_file="",
    )
    telemetry = engine.collect(result=result, runtime_config=runtime, metadata={"x": 1})

    assert telemetry.contract.emitted_events == len(result.context.events) - 1
    assert telemetry.contract.emitted_summary is False
    assert holder["logger"] is not None
    assert holder["logger"].summary_calls == 1
    assert any(item.startswith("telemetry_emit_event_failed:index=0:RuntimeError:event fail") for item in telemetry.warnings)
    assert any(item.startswith("telemetry_emit_summary_failed:RuntimeError:summary fail") for item in telemetry.warnings)
    assert any(item.startswith("telemetry_runtime_config_normalized:") for item in telemetry.warnings)


def test_telemetry_collect_falls_back_for_invalid_metrics_and_trace_payloads():
    result = _build_result()
    class _BadMetricsStub:
        def summarize(self, _result):
            return ["bad"]

    class _BadTraceStub:
        def build(self, _events, *, stage_order=None):
            return "bad"

    engine = DecisionPipelineTelemetryEngine(
        metrics_builder_factory=lambda: _BadMetricsStub(),  # type: ignore[arg-type]
        trace_builder_factory=lambda: _BadTraceStub(),  # type: ignore[arg-type]
    )
    runtime = RuntimeConfigContract(observability_enabled=False)

    telemetry = engine.collect(result=result, runtime_config=runtime)

    assert telemetry.contract.stage_count == 2
    assert telemetry.contract.event_count == 4
    assert telemetry.contract.total_stage_ms == 3.75
    assert any(item == "telemetry_metrics_invalid_payload" for item in telemetry.warnings)
    assert any(item == "telemetry_trace_invalid_payload" for item in telemetry.warnings)


def test_telemetry_collect_coerces_runtime_config_mapping():
    result = _build_result()
    engine = DecisionPipelineTelemetryEngine()

    telemetry = engine.collect(
        result=result,
        runtime_config={  # type: ignore[arg-type]
            "observability_enabled": False,
            "app_name": "era-test",
        },
    )

    assert telemetry.contract.emitted_events == 0
    assert telemetry.contract.emitted_summary is False
    assert any(item == "telemetry_runtime_config_coerced_from_mapping" for item in telemetry.warnings)


def test_telemetry_emit_events_retries_without_extra_kwarg():
    result = _build_result()
    captured = {"events": 0, "summaries": 0}

    class _LegacyLogger:
        def __init__(self, _settings):
            pass

        def log_event(self, _event):
            captured["events"] += 1

        def log_summary(self, **_kwargs):
            captured["summaries"] += 1

    engine = DecisionPipelineTelemetryEngine(logger_factory=_LegacyLogger)
    runtime = RuntimeConfigContract(
        observability_enabled=True,
        observability_emit_events=True,
        observability_emit_summary=True,
    )
    telemetry = engine.collect(result=result, runtime_config=runtime)

    assert telemetry.contract.emitted_events == len(result.context.events)
    assert telemetry.contract.emitted_summary is True
    assert captured["events"] == len(result.context.events)
    assert captured["summaries"] == 1
    assert any(
        item.startswith("telemetry_emit_event_without_extra:index=0:TypeError:")
        for item in telemetry.warnings
    )


def test_telemetry_fallback_metrics_ignores_invalid_event_and_error_collections():
    result = _build_result()
    result.context.events = "not-events"  # type: ignore[assignment]
    result.context.errors = {"e": "bad"}  # type: ignore[assignment]

    class _BadMetricsStub:
        def summarize(self, _result):
            return "bad"

    engine = DecisionPipelineTelemetryEngine(
        metrics_builder_factory=lambda: _BadMetricsStub(),  # type: ignore[arg-type]
    )
    runtime = RuntimeConfigContract(observability_enabled=False)
    telemetry = engine.collect(result=result, runtime_config=runtime)

    assert telemetry.contract.event_count == 0
    assert telemetry.contract.error_count == 0
    assert any(item == "telemetry_metrics_invalid_payload" for item in telemetry.warnings)


def test_telemetry_runtime_config_mapping_supports_normalized_keys():
    result = _build_result()
    engine = DecisionPipelineTelemetryEngine()

    telemetry = engine.collect(
        result=result,
        runtime_config={  # type: ignore[arg-type]
            "observability-enabled": "0",
            "observability-emit-events": "1",
            "app-name": "era-test",
        },
    )

    assert telemetry.contract.emitted_events == 0
    assert telemetry.contract.emitted_summary is False
    assert any(item == "telemetry_runtime_config_coerced_from_mapping" for item in telemetry.warnings)


def test_telemetry_sanitize_metadata_accepts_iterable_key_value_payload():
    result = _build_result()
    engine = DecisionPipelineTelemetryEngine()
    runtime = RuntimeConfigContract(observability_enabled=False)

    telemetry = engine.collect(
        result=result,
        runtime_config=runtime,
        metadata=[("run-id", "abc"), ("seed", 42)],  # type: ignore[arg-type]
    )

    assert "telemetry_metadata_invalid_type" not in telemetry.warnings


def test_telemetry_collect_preserves_partial_metrics_mapping_items():
    result = _build_result()

    class _PartialMetricsStub:
        def summarize(self, _result):
            return _PartialFailingMapping()

    engine = DecisionPipelineTelemetryEngine(
        metrics_builder_factory=lambda: _PartialMetricsStub(),  # type: ignore[arg-type]
    )
    runtime = RuntimeConfigContract(observability_enabled=False)

    telemetry = engine.collect(result=result, runtime_config=runtime)

    assert telemetry.contract.stage_count == 2
    assert telemetry.contract.status == "completed"
