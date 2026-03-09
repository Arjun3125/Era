"""Tests for core staged orchestrator runtime behavior."""

from __future__ import annotations

import pytest

from core.contracts import InputContract
from core.orchestrator.runtime import (
    ErrorPolicy,
    OrchestrationResult,
    PipelineOrchestrator,
    RunStatus,
    StageOutcome,
)


class _PartialFailingMapping(dict):
    def items(self):
        def _items():
            yield ("ok", 1)
            yield ("still_ok", 2)
            raise RuntimeError("items boom")

        return _items()


def test_register_stage_validates_name_handler_and_duplicates():
    orch = PipelineOrchestrator()

    with pytest.raises(ValueError, match="non-empty"):
        orch.register_stage("", lambda ctx: None)

    with pytest.raises(TypeError, match="callable"):
        orch.register_stage("s1", None)  # type: ignore[arg-type]

    orch.register_stage("s1", lambda ctx: None)
    with pytest.raises(ValueError, match="already registered"):
        orch.register_stage("s1", lambda ctx: None)


def test_register_stage_accepts_scalar_name_and_normalizes_to_text():
    orch = PipelineOrchestrator()
    orch.register_stage(0, lambda ctx: None)  # type: ignore[arg-type]
    assert orch.list_stages() == ["0"]


def test_register_stage_normalizes_error_policy_case():
    orch = PipelineOrchestrator()
    orch.register_stage("s1", lambda ctx: None, on_error="DEGRADE")
    assert orch._stages[0].on_error == ErrorPolicy.DEGRADE

    with pytest.raises(ValueError, match="on_error must be"):
        orch.register_stage("s2", lambda ctx: None, on_error="warn")


def test_run_aborts_on_abort_policy_even_when_outcome_marked_degraded():
    orch = PipelineOrchestrator(strict=False)
    orch.register_stage(
        "bad",
        lambda ctx: StageOutcome(errors=["x"], degraded=True),
        on_error="abort",
    )
    orch.register_stage("later", lambda ctx: {"after": True}, on_error="degrade")

    result = orch.run(InputContract(user_input="x"))
    assert result.status == RunStatus.ABORTED
    assert "later" not in result.context.state
    assert len(result.context.errors) == 1
    assert result.context.errors[0].recoverable is False


def test_run_degrade_policy_respects_strict_mode_for_recoverability_and_abort():
    orch_non_strict = PipelineOrchestrator(strict=False)
    orch_non_strict.register_stage(
        "d1",
        lambda ctx: StageOutcome(errors=["warn"]),
        on_error="degrade",
    )
    orch_non_strict.register_stage("d2", lambda ctx: {"ok": True}, on_error="degrade")

    result_non_strict = orch_non_strict.run(InputContract(user_input="x"))
    assert result_non_strict.status == RunStatus.COMPLETED_WITH_ERRORS
    assert result_non_strict.context.state["ok"] is True
    assert result_non_strict.context.errors[0].recoverable is True

    orch_strict = PipelineOrchestrator(strict=True)
    orch_strict.register_stage(
        "d1",
        lambda ctx: StageOutcome(errors=["warn"]),
        on_error="degrade",
    )
    orch_strict.register_stage("d2", lambda ctx: {"ok": True}, on_error="degrade")

    result_strict = orch_strict.run(InputContract(user_input="x"))
    assert result_strict.status == RunStatus.ABORTED
    assert "ok" not in result_strict.context.state
    assert result_strict.context.errors[0].recoverable is False


def test_run_sanitizes_stage_outcome_fields_and_clones_config_metadata():
    source_config = {"a": 1}
    source_metadata = {"m": 2}

    def _stage(ctx):
        ctx.config["a"] = 99
        ctx.metadata["m"] = 88
        return StageOutcome(outputs=None, errors="  issue  ")

    orch = PipelineOrchestrator()
    orch.register_stage("s1", _stage, on_error="degrade")
    result = orch.run(
        InputContract(user_input="x"),
        config=source_config,
        metadata=source_metadata,
    )

    assert result.status == RunStatus.COMPLETED_WITH_ERRORS
    assert source_config["a"] == 1
    assert source_metadata["m"] == 2
    assert result.context.errors[0].message == "issue"


def test_run_validates_config_and_metadata_mapping_types():
    orch = PipelineOrchestrator()
    orch.register_stage("s1", lambda ctx: None)

    with pytest.raises(TypeError, match="config must be a mapping"):
        orch.run(InputContract(user_input="x"), config=["bad"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="metadata must be a mapping"):
        orch.run(InputContract(user_input="x"), metadata=["bad"])  # type: ignore[arg-type]


def test_run_stringifies_output_keys_and_records_collision_warning():
    orch = PipelineOrchestrator()

    def _stage(_ctx):
        return StageOutcome(outputs={1: "a", "1": "b"})

    orch.register_stage("s1", _stage, on_error="degrade")
    result = orch.run(InputContract(user_input="x"))

    assert result.context.state["1"] == "b"
    assert any(
        "orchestrator_output_key_collision_after_stringify:stage=s1" in err.message
        for err in result.context.errors
    )


def test_orchestration_result_normalizes_status_and_timings():
    context = PipelineOrchestrator().run(InputContract(user_input="x")).context
    result = OrchestrationResult(
        run_id=123,  # type: ignore[arg-type]
        status="completed_with_errors",  # type: ignore[arg-type]
        context=context,
        stage_timings_ms={1: "2.1267", "": 3, "neg": -2},
        total_runtime_ms="bad",  # type: ignore[arg-type]
    )

    assert result.run_id == "123"
    assert result.status == RunStatus.COMPLETED_WITH_ERRORS
    assert result.stage_timings_ms == {"1": 2.127, "neg": 0.0}
    assert result.total_runtime_ms == 0.0


def test_orchestration_result_clamps_non_finite_timings_and_runtime():
    context = PipelineOrchestrator().run(InputContract(user_input="x")).context
    result = OrchestrationResult(
        run_id="run-non-finite",
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={"a": float("nan"), "b": float("inf"), "c": 1.23456},
        total_runtime_ms=float("nan"),
    )

    assert result.stage_timings_ms == {"a": 0.0, "b": 0.0, "c": 1.235}
    assert result.total_runtime_ms == 0.0


def test_orchestration_result_preserves_scalar_run_id_zero():
    context = PipelineOrchestrator().run(InputContract(user_input="x")).context
    result = OrchestrationResult(
        run_id=0,  # type: ignore[arg-type]
        status=RunStatus.COMPLETED,
        context=context,
    )
    assert result.run_id == "0"


def test_run_normalizes_iterable_error_payloads():
    orch = PipelineOrchestrator(strict=False)
    orch.register_stage(
        "s1",
        lambda ctx: StageOutcome(
            errors=(item for item in [b" boom ", {"message": "mapped"}, "", "boom"])
        ),
        on_error="degrade",
    )

    result = orch.run(InputContract(user_input="x"))
    assert result.status == RunStatus.COMPLETED_WITH_ERRORS
    assert [item.message for item in result.context.errors] == ["boom", "mapped"]


def test_runtime_normalize_mapping_and_outputs_accept_iterable_key_value_payloads():
    mapping = PipelineOrchestrator._normalize_mapping([(b"a", 1), ("b", 2)])  # type: ignore[arg-type]
    outputs = PipelineOrchestrator._normalize_outputs([(1, "x"), ("2", "y")])

    assert mapping == {"a": 1, "b": 2}
    assert outputs == {"1": "x", "2": "y"}


def test_run_collision_warning_uses_normalized_output_key_space():
    orch = PipelineOrchestrator()

    def _stage(_ctx):
        return StageOutcome(outputs={b"a": 1, "a": 2})

    orch.register_stage("s1", _stage, on_error="degrade")
    result = orch.run(InputContract(user_input="x"))

    assert result.context.state["a"] == 2
    assert any(
        "orchestrator_output_key_collision_after_stringify:stage=s1" in err.message
        for err in result.context.errors
    )


def test_runtime_normalize_mapping_rejects_invalid_iterable_item_shapes():
    assert PipelineOrchestrator._normalize_mapping([("a", 1), ("b", 2, 3)]) == {}


def test_run_preserves_partial_stage_output_mapping_items():
    orch = PipelineOrchestrator(strict=False)
    orch.register_stage(
        "s1",
        lambda ctx: StageOutcome(outputs=_PartialFailingMapping()),
        on_error="degrade",
    )

    result = orch.run(InputContract(user_input="x"))

    assert result.status == RunStatus.COMPLETED
    assert result.context.state["ok"] == 1
    assert result.context.state["still_ok"] == 2
