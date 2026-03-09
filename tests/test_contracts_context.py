"""Tests for execution context contract behavior."""

from __future__ import annotations

import pytest

from core.contracts import ErrorContract, EventRecord, EventType, ExecutionContext, InputContract


def test_execution_context_validates_mapping_fields_and_input_contract():
    with pytest.raises(TypeError, match="InputContract"):
        ExecutionContext(input_contract="bad")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="config"):
        ExecutionContext(input_contract=InputContract(user_input="x"), config=["bad"])  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="metadata"):
        ExecutionContext(input_contract=InputContract(user_input="x"), metadata=["bad"])  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="state"):
        ExecutionContext(input_contract=InputContract(user_input="x"), state=["bad"])  # type: ignore[arg-type]


def test_execution_context_emit_accepts_string_event_type_and_normalizes_payload():
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        current_stage=" default_stage ",
    )
    event = context.emit(
        "stage_started",
        payload={1: "a"},
        level="warning",
    )

    assert event.event_type == EventType.STAGE_STARTED
    assert event.stage == "default_stage"
    assert event.payload == {"1": "a"}
    assert event.level.value == "warning"


def test_execution_context_emit_accepts_iterable_key_value_payload():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    event = context.emit(
        "stage_started",
        payload=[(b"a", 1), ("a", 2), ("b", 3)],  # type: ignore[arg-type]
    )

    assert event.payload == {"a": 1, "b": 3}


def test_execution_context_add_error_coerces_mapping_and_string():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.add_error(" exploded ")
    context.add_error({"code": "x", "message": "y", "recoverable": 1, "details": {"a": 1}})
    context.add_error(ErrorContract(code="z", message="m"))

    assert len(context.errors) == 3
    assert context.errors[0].code == "runtime_error"
    assert context.errors[0].message == "exploded"
    assert context.errors[1].code == "x"
    assert context.errors[1].recoverable is True
    assert context.errors[2].code == "z"


def test_execution_context_add_error_accepts_bytes():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.add_error(b" exploded ")

    assert len(context.errors) == 1
    assert context.errors[0].code == "runtime_error"
    assert context.errors[0].message == "exploded"


def test_execution_context_validates_existing_events_collection():
    valid_event = EventRecord(run_id="r1", event_type=EventType.RUN_STARTED)
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        events=[valid_event],
    )
    assert len(context.events) == 1

    with pytest.raises(TypeError, match="EventRecord"):
        ExecutionContext(
            input_contract=InputContract(user_input="x"),
            events=[{"bad": True}],  # type: ignore[list-item]
        )


def test_execution_context_coerces_mapping_error_fields_defensively():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    context.add_error(
        {
            "code": 0,
            "message": 0,
            "recoverable": "false",
            "details": "bad",
        }
    )

    assert len(context.errors) == 1
    assert context.errors[0].code == "0"
    assert context.errors[0].message == "0"
    assert context.errors[0].recoverable is False
    assert context.errors[0].details == {}


def test_execution_context_accepts_iterable_events_and_errors():
    event = EventRecord(run_id="r1", event_type=EventType.RUN_STARTED)
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        events=(item for item in [event]),
        errors=(item for item in [{"message": "bad"}]),
    )

    assert len(context.events) == 1
    assert context.events[0].event_type == EventType.RUN_STARTED
    assert len(context.errors) == 1
    assert context.errors[0].message == "bad"


def test_execution_context_accepts_iterable_mapping_inputs_and_bytes_error_fields():
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        config=[("a", 1)],  # type: ignore[arg-type]
        metadata=[(b"m", 2)],  # type: ignore[arg-type]
        state=((b"s", 3),),  # type: ignore[arg-type]
    )
    context.add_error(
        {
            "code": b"ctx_error",
            "message": b"boom",
            "recoverable": b"1",
            "details": [("hint", "x")],
        }
    )

    assert context.config == {"a": 1}
    assert context.metadata == {"m": 2}
    assert context.state == {"s": 3}
    assert context.errors[-1].code == "ctx_error"
    assert context.errors[-1].message == "boom"
    assert context.errors[-1].recoverable is True
    assert context.errors[-1].details == {"hint": "x"}


def test_execution_context_mapping_normalization_preserves_first_normalized_key():
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        config=[(b"cfg", 1), ("cfg", 2)],  # type: ignore[arg-type]
    )

    assert context.config == {"cfg": 1}


def test_execution_context_rejects_faulty_iterable_mapping_inputs():
    class _FaultyMapping:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return ("cfg", 1)
            raise RuntimeError("boom")

    with pytest.raises(TypeError, match="config"):
        ExecutionContext(
            input_contract=InputContract(user_input="x"),
            config=_FaultyMapping(),  # type: ignore[arg-type]
        )


def test_execution_context_rejects_faulty_iterable_events_collection():
    event = EventRecord(run_id="r1", event_type=EventType.RUN_STARTED)

    class _FaultyEvents:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return event
            raise RuntimeError("boom")

    with pytest.raises(TypeError, match="events"):
        ExecutionContext(
            input_contract=InputContract(user_input="x"),
            events=_FaultyEvents(),  # type: ignore[arg-type]
        )
