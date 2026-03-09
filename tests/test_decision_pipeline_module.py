"""Tests for decision pipeline module wrapper behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.contracts import (
    ContractValidationContract,
    CouncilContract,
    CouncilNormalizationContract,
    DecisionContract,
    DecisionPackagingContract,
    DomainAnalysisContract,
    ExecutionContext,
    InputContract,
    KnowledgeContract,
    ModeResolutionContract,
    ModuleStatus,
    PipelineErrorSummaryContract,
    PipelineTelemetryContract,
    RequestContextContract,
    RuntimeConfigContract,
)
from modules.decision_pipeline.module import DecisionPipelineModule


class _EngineStub:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.pipeline_name = "decision_pipeline"

    def run(self, **kwargs):
        self.calls.append(dict(kwargs))
        return self.result


class _ExplodingEngine:
    pipeline_name = "decision_pipeline"

    def run(self, **kwargs):
        raise RuntimeError("pipeline blew up")


class _PartialFailingIterable:
    def __init__(self, *items):
        self._items = items

    def __iter__(self):
        for item in self._items:
            yield item
        raise RuntimeError("iterator boom")


class _PartialFailingMapping(dict):
    def items(self):
        def _items():
            yield ("domain_analysis_result", [("ok", 1)])
            yield ("stage_order", _PartialFailingIterable("s1", "s2"))
            yield ("errors", _PartialFailingIterable("err_a", "err_b"))
            raise RuntimeError("items boom")

        return _items()


def _build_pipeline_result(*, status: str, errors: list[str] | None = None):
    return SimpleNamespace(
        status=status,
        request_context_contract=RequestContextContract(warning_count=1),
        runtime_config_contract=RuntimeConfigContract(),
        contract_validation_contract=ContractValidationContract(warning_count=1, error_count=0),
        council_normalization_contract=CouncilNormalizationContract(minister_count=2),
        decision_packaging_contract=DecisionPackagingContract(requires_followup=True),
        error_summary_contract=PipelineErrorSummaryContract(
            issue_count=len(list(errors or [])),
            error_count=0,
            fatal_count=0,
        ),
        telemetry_contract=PipelineTelemetryContract(stage_count=3, total_stage_ms=9.5),
        domain_analysis_contract=DomainAnalysisContract(domains=["strategy"]),
        mode_resolution=ModeResolutionContract(mode="meeting", should_invoke_council=True),
        knowledge_contract=KnowledgeContract(),
        council_contract=CouncilContract(),
        decision_contract=DecisionContract(decision="defer"),
        domain_analysis_result={},
        knowledge_result={},
        council_result={},
        council_result_normalized={},
        decision_package={},
        final_decision={"final_outcome": "defer", "reason": "ok"},
        pipeline_issues=[],
        telemetry_metrics={"ok": True},
        telemetry_trace={"stages": []},
        stage_order=["s1", "s2"],
        stage_timings_ms={"s1": 1.0, "s2": 2.0},
        errors=list(errors or []),
    )


def test_validate_rejects_invalid_routing_context_type():
    module = DecisionPipelineModule(engine=_EngineStub(_build_pipeline_result(status="completed")))
    context = ExecutionContext(
        input_contract=InputContract(user_input="hello"),
        state={"routing_context": ["bad"]},
    )
    with pytest.raises(TypeError, match="routing_context must be a mapping"):
        module.validate(context)


def test_validate_accepts_explicit_empty_routing_context_mapping():
    module = DecisionPipelineModule(engine=_EngineStub(_build_pipeline_result(status="completed")))
    context = ExecutionContext(
        input_contract=InputContract(user_input="hello"),
        state={"routing_context": {}},
    )

    module.validate(context)


def test_execute_maps_aborted_pipeline_to_failed_and_normalizes_inputs():
    result = _build_pipeline_result(status="aborted")
    engine = _EngineStub(result)
    module = DecisionPipelineModule(engine=engine)
    context = ExecutionContext(
        input_contract=InputContract(user_input="hello", source="", metadata={"requested_mode": 4}),
        config={"routing_context": {1: "x"}},
        metadata={2: "m"},
    )

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.FAILED

    engine_call = engine.calls[0]
    assert engine_call["requested_mode"] == "4"
    assert engine_call["routing_context"] == {"1": "x"}
    assert engine_call["source"] == "interactive"
    assert engine_call["metadata"] == {"2": "m"}


def test_execute_maps_completed_with_errors_to_degraded():
    result = _build_pipeline_result(status="completed_with_errors")
    module = DecisionPipelineModule(engine=_EngineStub(result))
    context = ExecutionContext(input_contract=InputContract(user_input="hello"))

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.DEGRADED


def test_execute_metrics_are_defensive_for_malformed_payloads():
    result = _build_pipeline_result(status="completed")
    result.stage_timings_ms = ["bad"]  # type: ignore[assignment]
    result.telemetry_contract = PipelineTelemetryContract(stage_count=3, total_stage_ms="nan")  # type: ignore[arg-type]
    module = DecisionPipelineModule(engine=_EngineStub(result))
    context = ExecutionContext(input_contract=InputContract(user_input="hello"))

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.SUCCESS
    assert run_result.metrics["stage_count"] == 0
    assert run_result.metrics["telemetry_total_stage_ms"] == 0.0


def test_execute_normalizes_malformed_pipeline_result_shape():
    malformed = {
        "status": "completed",
        "request_context_contract": "bad-contract",
        "stage_timings_ms": ["bad"],
        "errors": "legacy-error",
        "pipeline_issues": "legacy-issue",
    }
    module = DecisionPipelineModule(engine=_EngineStub(malformed))
    context = ExecutionContext(input_contract=InputContract(user_input="hello"))

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.SUCCESS
    assert run_result.outputs["request_context_contract"].requested_mode == "meeting"
    assert run_result.outputs["decision_contract"].decision == "defer"
    assert run_result.outputs["pipeline_issues"][0]["message"] == "legacy-issue"
    assert run_result.errors == ["legacy-error"]


def test_execute_degrades_when_pipeline_engine_raises():
    module = DecisionPipelineModule(engine=_ExplodingEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="hello"))

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.FAILED
    assert run_result.outputs["decision_contract"].decision == "defer"
    assert run_result.outputs["error_summary_contract"].fatal_count == 1
    assert any("RuntimeError" in err for err in run_result.errors)


def test_execute_non_strict_resolution_uses_later_valid_candidates():
    result = _build_pipeline_result(status="completed")
    engine = _EngineStub(result)
    module = DecisionPipelineModule(engine=engine)
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="hello",
            metadata={"requested_mode": "quick", "routing_context": {"from_input": 3}},
        ),
        state={
            "requested_mode": {"bad": True},
            "routing_context": ["bad"],
        },
        config={"routing_context": {"from_config": 2}},
        metadata={"requested_mode": "meeting"},
    )

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.SUCCESS
    engine_call = engine.calls[0]
    assert engine_call["requested_mode"] == "meeting"
    assert engine_call["routing_context"] == {"from_config": 2}


def test_execute_accepts_normalized_requested_mode_and_routing_context_keys():
    result = _build_pipeline_result(status="completed")
    engine = _EngineStub(result)
    module = DecisionPipelineModule(engine=engine)
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="hello",
            metadata={"requested-mode": "quick", "routing-context": {"from_input": 3}},
        ),
        state={"requested-mode": "war"},
        config={"routing-context": {"from_config": 2}},
        metadata={},
    )

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.SUCCESS
    engine_call = engine.calls[0]
    assert engine_call["requested_mode"] == "war"
    assert engine_call["routing_context"] == {"from_config": 2}


def test_execute_normalizes_dashed_pipeline_result_fields():
    malformed = {
        "status": "completed",
        "request-context-contract": "bad-contract",
        "runtime-config-contract": RuntimeConfigContract(),
        "mode-resolution": ModeResolutionContract(mode="quick", should_invoke_council=False),
        "decision-contract": DecisionContract(decision="accept"),
        "decision-package": {"final_outcome": "accept"},
        "final-decision": {"final_outcome": "accept", "reason": "ok"},
        "stage-order": ["s1"],
        "stage-timings-ms": {"s1": 1.0},
    }
    module = DecisionPipelineModule(engine=_EngineStub(malformed))
    context = ExecutionContext(input_contract=InputContract(user_input="hello"))

    run_result = module.execute(context)
    assert run_result.status == ModuleStatus.SUCCESS
    assert run_result.outputs["mode_contract"].mode == "quick"
    assert run_result.outputs["decision_contract"].decision == "accept"
    assert run_result.outputs["decision_package"]["final_outcome"] == "accept"


def test_execute_preserves_partial_iterable_pipeline_result_fields():
    malformed = _PartialFailingMapping()
    module = DecisionPipelineModule(engine=_EngineStub(malformed))
    context = ExecutionContext(input_contract=InputContract(user_input="hello"))

    run_result = module.execute(context)

    assert run_result.status == ModuleStatus.SUCCESS
    assert run_result.outputs["domain_analysis_result"] == {"ok": 1}
    assert run_result.outputs["stage_order"] == ["s1", "s2"]
    assert run_result.errors == ["err_a", "err_b"]
