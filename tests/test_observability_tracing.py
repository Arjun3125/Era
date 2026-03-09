"""Tests for event trace builder behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from core.contracts import EventType, ExecutionContext, InputContract
from core.observability.tracing import EventTraceBuilder


@dataclass
class _LooseEvent:
    stage: str
    event_type: str
    timestamp: str


def test_event_trace_builder_builds_ordered_trace_with_missing_and_incomplete():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.emit(EventType.STAGE_STARTED, stage="s1")
    context.emit(EventType.STAGE_DEGRADED, stage="s1")
    context.emit(EventType.STAGE_COMPLETED, stage="s1")  # should remain degraded
    context.emit(EventType.STAGE_STARTED, stage="s2")
    context.emit(EventType.STAGE_FAILED, stage="s3")

    events = list(context.events) + [
        _LooseEvent(stage="s2", event_type="custom_event", timestamp="2026-01-01T00:00:00Z"),
        _LooseEvent(stage=" ", event_type="stage_completed", timestamp="2026-01-01T00:00:01Z"),
    ]
    trace = EventTraceBuilder().build(
        events,
        stage_order=["s2", "s1", "s4", "s2"],
    )

    stages = trace["stages"]
    assert [item["stage"] for item in stages] == ["s2", "s1", "s3"]
    by_stage = {item["stage"]: item for item in stages}

    assert by_stage["s1"]["status"] == "degraded"
    assert by_stage["s2"]["status"] == "running"
    assert by_stage["s3"]["status"] == "failed"
    assert by_stage["s2"]["last_event_type"] == "custom_event"

    assert trace["incomplete_stages"] == ["s2"]
    assert trace["missing_stages"] == ["s4"]
    assert trace["event_count"] == len(events)


def test_event_trace_builder_ignores_string_events_and_stage_order_inputs():
    trace = EventTraceBuilder().build(
        events="not-events",  # type: ignore[arg-type]
        stage_order="s1,s2",  # type: ignore[arg-type]
    )

    assert trace["stages"] == []
    assert trace["incomplete_stages"] == []
    assert trace["missing_stages"] == []
    assert trace["event_count"] == 0


def test_event_trace_builder_accepts_single_non_sequence_event():
    single = _LooseEvent(stage="s1", event_type="stage_failed", timestamp="2026-01-01T00:00:00Z")
    trace = EventTraceBuilder().build(events=single, stage_order=["s1"])  # type: ignore[arg-type]

    assert trace["event_count"] == 1
    assert trace["stages"][0]["stage"] == "s1"
    assert trace["stages"][0]["status"] == "failed"


def test_event_trace_builder_accepts_iterable_events_and_stage_order():
    events = iter(
        [
            _LooseEvent(stage="s1", event_type="stage_started", timestamp="2026-01-01T00:00:00Z"),
            _LooseEvent(stage="s1", event_type="stage_completed", timestamp="2026-01-01T00:00:01Z"),
        ]
    )
    stage_order = iter(["s1", "s2"])
    trace = EventTraceBuilder().build(events=events, stage_order=stage_order)  # type: ignore[arg-type]

    assert trace["event_count"] == 2
    assert [item["stage"] for item in trace["stages"]] == ["s1"]
    assert trace["stages"][0]["status"] == "completed"
    assert trace["missing_stages"] == ["s2"]


def test_event_trace_builder_ignores_bytes_inputs_and_mapping_stage_order():
    trace = EventTraceBuilder().build(
        events=b"bad-events",  # type: ignore[arg-type]
        stage_order={"s1": True},  # type: ignore[arg-type]
    )

    assert trace["event_count"] == 0
    assert trace["stages"] == []
    assert trace["missing_stages"] == []


def test_event_trace_builder_accepts_mapping_events():
    trace = EventTraceBuilder().build(
        events=[
            {"stage": "s1", "event-type": b"stage_started", "timestamp": "2026-01-01T00:00:00Z"},
            {"stage_name": "s1", "event_type": "stage_completed", "timestamp": "2026-01-01T00:00:01Z"},
        ],
        stage_order=["s1", "s2"],
    )

    assert trace["event_count"] == 2
    assert [item["stage"] for item in trace["stages"]] == ["s1"]
    assert trace["stages"][0]["status"] == "completed"
    assert trace["stages"][0]["completed_at"] == "2026-01-01T00:00:01Z"
    assert trace["missing_stages"] == ["s2"]


def test_event_trace_builder_accepts_single_mapping_event():
    trace = EventTraceBuilder().build(
        events={"stage": "s1", "event_type": "stage_failed", "timestamp": "2026-01-01T00:00:00Z"},
        stage_order=["s1"],
    )

    assert trace["event_count"] == 1
    assert trace["stages"][0]["stage"] == "s1"
    assert trace["stages"][0]["status"] == "failed"


def test_event_trace_builder_parses_scalar_and_bytes_stage_fields():
    @dataclass
    class _ScalarEvent:
        stage: int
        event_type: bytes
        timestamp: int

    trace = EventTraceBuilder().build(
        events=[_ScalarEvent(stage=0, event_type=b"stage_completed", timestamp=0)],
        stage_order=[0, "s2"],  # type: ignore[list-item]
    )

    assert trace["event_count"] == 1
    assert [item["stage"] for item in trace["stages"]] == ["0"]
    assert trace["stages"][0]["status"] == "completed"
    assert trace["stages"][0]["started_at"] == "0"
    assert trace["stages"][0]["completed_at"] == "0"
    assert trace["missing_stages"] == ["s2"]


def test_event_trace_builder_accepts_event_type_aliases():
    trace = EventTraceBuilder().build(
        events=[
            {"stage": "s1", "event": "stage_start", "timestamp": "2026-01-01T00:00:00Z"},
            {"stage": "s1", "name": "stage_done", "timestamp": "2026-01-01T00:00:01Z"},
        ],
        stage_order=["s1"],
    )

    assert trace["event_count"] == 2
    assert trace["stages"][0]["stage"] == "s1"
    assert trace["stages"][0]["status"] == "completed"
    assert trace["stages"][0]["completed_at"] == "2026-01-01T00:00:01Z"


def test_event_trace_builder_keeps_partial_items_from_faulty_iterables():
    class _FaultyEvents:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return {"stage": "s1", "event_type": "stage_started", "timestamp": "t1"}
            raise RuntimeError("boom")

    class _FaultyOrder:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return "s1"
            raise RuntimeError("boom")

    trace = EventTraceBuilder().build(
        events=_FaultyEvents(),  # type: ignore[arg-type]
        stage_order=_FaultyOrder(),  # type: ignore[arg-type]
    )

    assert trace["event_count"] == 1
    assert [item["stage"] for item in trace["stages"]] == ["s1"]
    assert trace["stages"][0]["status"] == "running"


def test_event_trace_builder_preserves_partial_normalized_mapping_items():
    class _FaultyNormalizedEvent(Mapping):
        def __getitem__(self, key):
            data = {
                "stage-name": "s1",
                "event-type": "stage_started",
                "occurred-at": "t1",
            }
            return data[key]

        def __iter__(self):
            yield "stage-name"
            yield "event-type"
            yield "occurred-at"
            raise RuntimeError("event-iter-failed")

        def __len__(self):
            return 3

        def items(self):
            yield ("stage-name", "s1")
            yield ("event-type", "stage_started")
            yield ("occurred-at", "t1")
            raise RuntimeError("event-items-failed")

    trace = EventTraceBuilder().build(
        events=[_FaultyNormalizedEvent()],  # type: ignore[list-item]
        stage_order=["s1"],
    )

    assert trace["event_count"] == 1
    assert [item["stage"] for item in trace["stages"]] == ["s1"]
    assert trace["stages"][0]["status"] == "running"
    assert trace["stages"][0]["started_at"] == "t1"
