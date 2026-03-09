"""Tests for structured observability event logger."""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping

import pytest

from config import RuntimeSettings
from core.contracts import EventType, ExecutionContext, InputContract
from core.observability.logger import StructuredEventLogger


def _event_with_payload(payload):
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    return context.emit(EventType.STAGE_COMPLETED, stage="s1", payload=payload)


def test_logger_writes_sanitized_event_record_to_file(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)

    event = _event_with_payload({"score": float("nan"), "blob": b"ok"})
    logger.log_event(event, extra={"extra_score": float("inf")})

    lines = file_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["kind"] == "orchestration_event"
    assert payload["payload"]["score"] == 0.0
    assert payload["payload"]["blob"] == "ok"
    assert payload["extra_score"] == 0.0


def test_logger_normalizes_event_text_fields_and_sanitizes_iterables(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings, sanitize_max_items=2)

    class _RawEvent:
        event_type = b"stage_completed"
        level = b"WARNING"
        payload = {"items": (item for item in [1, 2, 3])}
        timestamp = None
        run_id = 0
        event_id = b"evt-1"
        stage = 0

    logger.log_event(_RawEvent(), extra={1: "x"})  # type: ignore[arg-type]
    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["run_id"] == "0"
    assert payload["event_id"] == "evt-1"
    assert payload["stage"] == "0"
    assert payload["level"] == "warning"
    assert payload["payload"]["items"] == [1, 2]
    assert payload["1"] == "x"


def test_logger_coerces_non_mapping_summary_payloads(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)
    logger.log_summary(
        run_id="r1",
        status="completed",
        metrics=["bad"],  # type: ignore[arg-type]
        trace=None,  # type: ignore[arg-type]
        metadata="bad",  # type: ignore[arg-type]
    )

    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["kind"] == "orchestration_summary"
    assert payload["metrics"] == {}
    assert payload["trace"] == {}
    assert payload["metadata"] == {}


def test_logger_reports_file_sink_failure_after_stderr_emit(monkeypatch, capsys, tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=True,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)
    event = _event_with_payload({"x": 1})

    original_open = Path.open

    def _failing_open(self, *args, **kwargs):
        if self == file_path:
            raise OSError("disk full")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _failing_open)
    with pytest.raises(OSError, match="disk full"):
        logger.log_event(event)

    stderr = capsys.readouterr().err
    assert '"kind": "orchestration_event"' in stderr


def test_logger_truncates_large_strings_and_sequences(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings, sanitize_max_items=3, sanitize_max_string=5)
    event = _event_with_payload(
        {
            "long_text": "abcdefghijklmnopqrstuvwxyz",
            "many_items": [1, 2, 3, 4, 5],
        }
    )
    logger.log_event(event)

    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["payload"]["long_text"] == "abcde"
    assert payload["payload"]["many_items"] == [1, 2, 3]


def test_logger_accepts_iterable_payload_and_extra_mappings(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)

    class _RawEvent:
        event_type = "stage_completed"
        level = "info"
        payload = [(b"a", 1), ("b", 2)]
        timestamp = "2026-01-01T00:00:00+00:00"
        run_id = "r1"
        event_id = "e1"
        stage = "s1"

    logger.log_event(_RawEvent(), extra=[(b"x", 9)])  # type: ignore[arg-type]
    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["payload"] == {"a": 1, "b": 2}
    assert payload["x"] == 9


def test_logger_summary_accepts_iterable_mapping_payloads(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)

    logger.log_summary(
        run_id="r2",
        status="completed",
        metrics=[("score", 1.0)],  # type: ignore[arg-type]
        trace=((b"stages", ["s1"]),),  # type: ignore[arg-type]
        metadata=[("seed", 42)],  # type: ignore[arg-type]
    )
    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["metrics"] == {"score": 1.0}
    assert payload["trace"] == {"stages": ["s1"]}
    assert payload["metadata"] == {"seed": 42}


def test_logger_falls_back_to_value_for_invalid_iterable_payload_shape(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)

    class _RawEvent:
        event_type = "stage_completed"
        level = "info"
        payload = [("ok", 1), ("bad", 2, 3)]
        timestamp = "2026-01-01T00:00:00+00:00"
        run_id = "r3"
        event_id = "e3"
        stage = "s3"

    logger.log_event(_RawEvent())  # type: ignore[arg-type]
    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["payload"]["value"] == [["ok", 1], ["bad", 2, 3]]


def test_logger_preserves_partial_iterable_payload_and_extra_mappings(tmp_path):
    file_path = tmp_path / "obs.jsonl"
    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=True,
        observability_stderr=False,
        observability_file=str(file_path),
    )
    logger = StructuredEventLogger(settings)

    class _PartialPayload:
        def __iter__(self):
            yield ("a", 1)
            yield ("b", 2)
            raise RuntimeError("payload-iter-failed")

    class _PartialExtra(Mapping):
        def __getitem__(self, key):
            data = {"x": 9, "y": 10}
            return data[key]

        def __iter__(self):
            yield "x"
            yield "y"
            raise RuntimeError("extra-iter-failed")

        def __len__(self) -> int:
            return 2

        def items(self):
            yield ("x", 9)
            yield ("y", 10)
            raise RuntimeError("extra-items-failed")

    class _RawEvent:
        event_type = "stage_completed"
        level = "info"
        payload = _PartialPayload()
        timestamp = "2026-01-01T00:00:00+00:00"
        run_id = "r4"
        event_id = "e4"
        stage = "s4"

    logger.log_event(_RawEvent(), extra=_PartialExtra())  # type: ignore[arg-type]
    payload = json.loads(file_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["payload"] == {"a": 1, "b": 2}
    assert payload["x"] == 9
    assert payload["y"] == 10
