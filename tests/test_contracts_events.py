"""Tests for core event contracts."""

from __future__ import annotations

from datetime import datetime

import pytest

from core.contracts.events import EventLevel, EventRecord, EventType


def test_event_type_and_level_coercion():
    assert EventType.coerce("stage_started") == EventType.STAGE_STARTED
    assert EventType.coerce("STAGE-STARTED") == EventType.STAGE_STARTED
    assert EventType.coerce("stage started") == EventType.STAGE_STARTED
    assert EventType.coerce("run_abort") == EventType.RUN_ABORTED
    assert EventType.coerce(EventType.RUN_COMPLETED) == EventType.RUN_COMPLETED
    assert EventType.coerce(b"stage_started") == EventType.STAGE_STARTED
    assert EventLevel.coerce("warning") == EventLevel.WARNING
    assert EventLevel.coerce("warn") == EventLevel.WARNING
    assert EventLevel.coerce("ERR") == EventLevel.ERROR
    assert EventLevel.coerce(b"warning") == EventLevel.WARNING
    assert EventLevel.coerce("unknown") == EventLevel.INFO

    with pytest.raises(ValueError, match="Unsupported event type"):
        EventType.coerce("unknown")


def test_event_record_normalizes_fields_and_payload():
    record = EventRecord(
        run_id="  run-x  ",
        event_type="stage_completed",
        payload={1: "a", "b": "c"},
        stage="  s1  ",
        level="error",
        event_id="",
        timestamp="",
    )

    assert record.run_id == "run-x"
    assert record.event_type == EventType.STAGE_COMPLETED
    assert record.payload == {"1": "a", "b": "c"}
    assert record.stage == "s1"
    assert record.level == EventLevel.ERROR
    assert record.event_id
    assert record.timestamp


def test_event_record_wraps_non_mapping_payload_and_rejects_empty_run_id():
    record = EventRecord(
        run_id="run-y",
        event_type=EventType.RUN_STARTED,
        payload=["x"],
    )
    assert record.payload == {"value": ["x"]}

    with pytest.raises(ValueError, match="run_id must be non-empty"):
        EventRecord(run_id=" ", event_type=EventType.RUN_STARTED)


def test_event_record_normalizes_scalar_ids_and_datetime_timestamp():
    record = EventRecord(
        run_id=0,  # type: ignore[arg-type]
        event_type=EventType.RUN_STARTED,
        payload={1: "first", "1": "second"},
        stage=0,  # type: ignore[arg-type]
        event_id=0,  # type: ignore[arg-type]
        timestamp=datetime(2026, 1, 1, 0, 0, 0),
    )

    assert record.run_id == "0"
    assert record.stage == "0"
    assert record.event_id == "0"
    assert record.payload["1"] == "first"
    assert record.timestamp.endswith("+00:00")


def test_event_record_normalizes_bytes_and_iterable_payload_mapping():
    record = EventRecord(
        run_id=b"run-b",
        event_type=b"stage_started",
        payload=[(b"a", 1), ("a", 2), ("b", 3)],
        stage=b"stage-1",
        event_id=b"evt-1",
        timestamp=b"2026-01-01T00:00:00+00:00",
    )

    assert record.run_id == "run-b"
    assert record.event_type == EventType.STAGE_STARTED
    assert record.payload == {"a": 1, "b": 3}
    assert record.stage == "stage-1"
    assert record.event_id == "evt-1"
    assert record.timestamp == "2026-01-01T00:00:00+00:00"


def test_event_record_wraps_invalid_iterable_payload_shape():
    payload = [("a", 1, 2)]
    record = EventRecord(
        run_id="run-z",
        event_type=EventType.RUN_STARTED,
        payload=payload,  # type: ignore[arg-type]
    )

    assert record.payload == {"value": payload}


def test_event_record_wraps_faulty_iterable_payload_instead_of_partial_mapping():
    class _FaultyPayload:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return ("a", 1)
            raise RuntimeError("boom")

    payload = _FaultyPayload()
    record = EventRecord(
        run_id="run-faulty",
        event_type=EventType.RUN_STARTED,
        payload=payload,  # type: ignore[arg-type]
    )

    assert record.payload == {"value": payload}
