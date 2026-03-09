"""Tests for orchestration metrics normalization."""

from __future__ import annotations

from core.contracts import ExecutionContext, InputContract
from core.orchestrator.runtime import OrchestrationResult, RunStatus
from core.observability.metrics import OrchestrationMetrics


def test_orchestration_metrics_normalizes_invalid_timings_and_counts():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.events.extend([object(), object(), object()])
    context.errors.extend([object()])

    result = OrchestrationResult(
        run_id="run-1",
        status=RunStatus.COMPLETED_WITH_ERRORS,
        context=context,
        stage_timings_ms={
            "stage_a": "1.25",
            "stage_b": float("nan"),
            "stage_c": -4,
            "stage_d": "bad",
            "": 10,  # ignored empty stage name
        },
        total_runtime_ms=5.0,
    )

    metrics = OrchestrationMetrics().summarize(result)

    assert metrics["run_id"] == "run-1"
    assert metrics["status"] == "completed_with_errors"
    assert metrics["stage_count"] == 4
    assert metrics["event_count"] == 3
    assert metrics["error_count"] == 1
    assert metrics["total_stage_ms"] == 1.25
    assert metrics["total_runtime_ms"] == 5.0
    assert metrics["runtime_overhead_ms"] == 3.75
    assert metrics["slowest_stage"] == "stage_a"
    assert metrics["slowest_stage_ms"] == 1.25
    assert metrics["stage_timings_ms"]["stage_b"] == 0.0
    assert metrics["stage_timings_ms"]["stage_c"] == 0.0


def test_orchestration_metrics_handles_missing_runtime_and_context_fields():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    result = OrchestrationResult(
        run_id="run-2",
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={"s": 2},
        total_runtime_ms=0.0,
    )

    metrics = OrchestrationMetrics().summarize(result)
    assert metrics["stage_count"] == 1
    assert metrics["total_stage_ms"] == 2.0
    assert metrics["total_runtime_ms"] == 0.0
    assert metrics["runtime_overhead_ms"] == 0.0


def test_orchestration_metrics_handles_non_sequence_context_events_and_errors():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.events = "not-sequence"  # type: ignore[assignment]
    context.errors = 42  # type: ignore[assignment]
    result = OrchestrationResult(
        run_id="run-3",
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={"s1": 1},
        total_runtime_ms=1.5,
    )

    metrics = OrchestrationMetrics().summarize(result)
    assert metrics["event_count"] == 0
    assert metrics["error_count"] == 0


def test_orchestration_metrics_accepts_iterables_and_ignores_mapping_like_payloads():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.events = (item for item in [object(), object()])  # type: ignore[assignment]
    context.errors = {"a": 1, "b": 2}  # type: ignore[assignment]
    result = OrchestrationResult(
        run_id="run-4",
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={"s1": 1},
        total_runtime_ms=1.0,
    )

    metrics = OrchestrationMetrics().summarize(result)
    assert metrics["event_count"] == 2
    assert metrics["error_count"] == 0


def test_orchestration_metrics_preserves_scalar_and_bytes_identifiers():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    result = OrchestrationResult(
        run_id=0,  # type: ignore[arg-type]
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={0: 1, b"s2": 2},  # type: ignore[dict-item]
        total_runtime_ms=3,
    )

    metrics = OrchestrationMetrics().summarize(result)
    assert metrics["run_id"] == "0"
    assert metrics["stage_count"] == 2
    assert metrics["stage_timings_ms"]["0"] == 1.0
    assert metrics["stage_timings_ms"]["s2"] == 2.0


def test_orchestration_metrics_normalize_timings_accepts_iterable_key_values():
    timings = OrchestrationMetrics._normalize_timings([(b"s1", "1.5"), ("s2", -2), ("", 3)])
    assert timings == {"s1": 1.5, "s2": 0.0}


def test_orchestration_metrics_normalize_timings_rejects_invalid_iterable_shapes():
    timings = OrchestrationMetrics._normalize_timings([("s1", 1), ("s2", 2, 3)])
    assert timings == {}


def test_orchestration_metrics_coerce_sequence_keeps_partial_items_from_faulty_iterable():
    class _FaultyIterable:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return "ok"
            raise RuntimeError("boom")

    values = OrchestrationMetrics._coerce_sequence(_FaultyIterable())
    assert values == ["ok"]


def test_orchestration_metrics_preserves_partial_iterable_timing_mappings():
    class _PartialTimings(dict):
        def items(self):
            yield ("s1", "1.5")
            yield ("s2", 2)
            raise RuntimeError("timings-items-failed")

    timings = OrchestrationMetrics._normalize_timings(_PartialTimings())  # type: ignore[arg-type]
    assert timings == {"s1": 1.5, "s2": 2.0}
