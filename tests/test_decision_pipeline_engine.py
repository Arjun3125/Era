"""Tests for decision pipeline engine boundary normalization and safety."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import modules.decision_pipeline as decision_pipeline_pkg
from core.contracts import (
    ExecutionContext,
    InputContract,
    PipelineErrorSummaryContract,
    PipelineTelemetryContract,
)
from core.orchestrator.runtime import OrchestrationResult, RunStatus, StageOutcome
from modules.decision_pipeline.engine import DecisionPipelineEngine


class _PipelineStub:
    def __init__(self, result: OrchestrationResult):
        self.result = result
        self.calls = []

    def run(self, input_contract, *, metadata=None, config=None):
        self.calls.append(
            {
                "input_contract": input_contract,
                "metadata": metadata,
                "config": config,
            }
        )
        return self.result


class _TelemetryStub:
    def collect(self, *, result, runtime_config, metadata):
        return SimpleNamespace(
            contract=PipelineTelemetryContract(stage_count=1, total_stage_ms=1.0),
            metrics=["not_a_mapping"],
            trace="not_a_mapping",
            warnings=[],
        )


class _ErrorStub:
    def collect(self, *, result, additional_warnings=None):
        return SimpleNamespace(
            summary=PipelineErrorSummaryContract(),
            issues=[],
            messages=[],
        )


class _PartialFailingIterable:
    def __init__(self, *items):
        self._items = items

    def __iter__(self):
        for item in self._items:
            yield item
        raise RuntimeError("iterator boom")


def _engine_for_test() -> DecisionPipelineEngine:
    return DecisionPipelineEngine(
        input_module=object(),  # type: ignore[arg-type]
        config_module=object(),  # type: ignore[arg-type]
        domain_module=object(),  # type: ignore[arg-type]
        mode_module=object(),  # type: ignore[arg-type]
        knowledge_module=object(),  # type: ignore[arg-type]
        validation_module=object(),  # type: ignore[arg-type]
        council_module=object(),  # type: ignore[arg-type]
        council_normalization_module=object(),  # type: ignore[arg-type]
        prime_module=object(),  # type: ignore[arg-type]
        decision_packaging_module=object(),  # type: ignore[arg-type]
        telemetry_engine=_TelemetryStub(),  # type: ignore[arg-type]
        error_engine=_ErrorStub(),  # type: ignore[arg-type]
    )


def test_engine_run_requires_string_user_input():
    engine = _engine_for_test()
    with pytest.raises(TypeError, match="user_input must be a string"):
        engine.run(user_input=123)  # type: ignore[arg-type]


def test_engine_run_normalizes_boundary_inputs_and_malformed_state():
    engine = _engine_for_test()
    context = ExecutionContext(
        input_contract=InputContract(user_input="seed"),
        state={
            "routing_context": ["bad"],
            "mode_resolution_confidence": "bad",
            "selected_ministers": "invalid",
            "runtime_settings": {"overrides_applied": "abc"},
            "decision_package": ["bad"],
            "council_result": {"consensus_strength": "bad", "minister_positions": "bad"},
            "prime_decision": {"confidence": "bad"},
            "domain_analysis_result": ["bad"],
            "knowledge_result": ["bad"],
        },
    )
    orchestration_result = OrchestrationResult(
        run_id=context.run_id,
        status=RunStatus.COMPLETED,
        context=context,
        stage_timings_ms={"s1": 1.0},
        total_runtime_ms=2.0,
    )
    pipeline = _PipelineStub(orchestration_result)
    engine._pipeline_instance = lambda: pipeline  # type: ignore[method-assign]

    result = engine.run(
        user_input="hello",
        requested_mode=123,  # type: ignore[arg-type]
        routing_context=["bad"],  # type: ignore[arg-type]
        metadata=["bad"],  # type: ignore[arg-type]
        source="",
    )

    call = pipeline.calls[0]
    assert call["input_contract"].source == "interactive"
    assert call["metadata"] == {"requested_mode": "123"}
    assert call["config"] == {"routing_context": {}}

    assert result.mode_resolution.confidence == 1.0
    assert result.runtime_config_contract.overrides_applied == []
    assert result.telemetry_metrics == {}
    assert result.telemetry_trace == {}
    assert result.stage_timings_ms == {"s1": 1.0}


def test_prepare_context_normalizes_routing_context_and_requested_mode():
    engine = _engine_for_test()
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="x",
            metadata={"routing_context": {"from_input": 1}},
        ),
        config={"routing_context": {"from_config": 2}},
        metadata={"requested_mode": 9},
        state={"routing_context": ["bad"]},
    )
    engine._prepare_context(context)

    assert context.state["requested_mode"] == "9"
    assert context.state["routing_context"] == {"from_config": 2, "from_input": 1}


def test_prepare_context_uses_input_metadata_requested_mode_when_missing_in_state_and_metadata():
    engine = _engine_for_test()
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="x",
            metadata={"requested_mode": "quick", "routing_context": {"from_input": 1}},
        ),
        config={"routing_context": {"from_config": 2}},
        metadata={},
        state={},
    )

    engine._prepare_context(context)
    assert context.state["requested_mode"] == "quick"
    assert context.state["routing_context"] == {"from_config": 2, "from_input": 1}


def test_prepare_context_ignores_non_finite_requested_mode_scalars():
    engine = _engine_for_test()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        metadata={"requested_mode": float("nan")},
        state={},
    )

    engine._prepare_context(context)
    assert "requested_mode" not in context.state


def test_resolve_domain_contract_accepts_iterable_domains():
    contract = DecisionPipelineEngine._resolve_domain_contract(
        {
            "routing_context": {
                "domains": iter(["strategy", "risk"]),
            }
        }
    )
    assert contract.domains == ["strategy", "risk"]


def test_resolve_decision_packaging_contract_reads_normalized_keys_and_strict_followup_bool():
    contract = DecisionPipelineEngine._resolve_decision_packaging_contract(
        {
            "decision-package": {
                "final-outcome": "accept",
                "mode": "meeting",
                "confidence": "0.7",
                "recommendation": "support",
                "council-outcome": "consensus_reached",
                "red-line-concerns": {"risk": True},
                "knowledge-items-used": "2",
                "requires-followup": 2,
            }
        }
    )

    assert contract.final_outcome == "accept"
    assert contract.red_line_count == 1
    assert contract.knowledge_item_count == 2
    assert contract.requires_followup is False


def test_prepare_context_reads_normalized_requested_mode_and_routing_context_keys():
    engine = _engine_for_test()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x", metadata={"routing-context": {"from_input": 1}}),
        config={"routing-context": {"from_config": 2}},
        metadata={"requested-mode": "darbar"},
        state={},
    )

    engine._prepare_context(context)
    assert context.state["requested_mode"] == "darbar"
    assert context.state["routing_context"] == {"from_config": 2, "from_input": 1}


def test_merge_council_normalization_accepts_iterable_payloads():
    context = ExecutionContext(input_contract=InputContract(user_input="x"))
    outcome = StageOutcome(
        outputs={
            "council_result_normalized": [
                ("outcome", "consensus_reached"),
                ("recommendation", "support"),
            ],
            "minister_outputs_normalized": [
                ("risk", [("stance", "support"), ("confidence", "0.7")]),
            ],
            "council_positions_normalized": (item for item in [{"minister": "risk"}]),
        }
    )

    merged = DecisionPipelineEngine._merge_council_normalization_into_state(context, outcome)
    assert merged.outputs["council_result_normalized"]
    assert context.state["council_result"]["outcome"] == "consensus_reached"
    assert context.state["minister_outputs"]["risk"][0] == ("stance", "support")
    assert context.state["council_result"]["council_positions"] == [{"minister": "risk"}]


def test_resolve_knowledge_contract_preserves_partial_iterable_active_domains():
    contract = DecisionPipelineEngine._resolve_knowledge_contract(
        {
            "knowledge_result": {
                "active_domains": _PartialFailingIterable("strategy", "risk"),
            }
        }
    )

    assert contract.active_domains == ["strategy", "risk"]


def test_package_factory_delegates_to_engine_create(monkeypatch):
    sentinel = object()

    def _fake_create(**kwargs):
        assert kwargs["risk_threshold"] == 0.55
        assert kwargs["strict"] is True
        return sentinel

    monkeypatch.setattr(decision_pipeline_pkg.DecisionPipelineEngine, "create", _fake_create)

    built = decision_pipeline_pkg.create_decision_pipeline(
        risk_threshold=0.55,
        strict=True,
    )
    assert built is sentinel


def test_package_factory_normalizes_strict_alias_value(monkeypatch):
    sentinel = object()

    def _fake_create(**kwargs):
        assert kwargs["risk_threshold"] == 0.7
        assert kwargs["strict"] is True
        return sentinel

    monkeypatch.setattr(decision_pipeline_pkg.DecisionPipelineEngine, "create", _fake_create)
    built = decision_pipeline_pkg.create_decision_pipeline(strict="yes")  # type: ignore[arg-type]
    assert built is sentinel


def test_package_factory_validates_risk_threshold_and_strict():
    with pytest.raises(TypeError, match="risk_threshold"):
        decision_pipeline_pkg.create_decision_pipeline(risk_threshold="bad")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        decision_pipeline_pkg.create_decision_pipeline(risk_threshold=1.2)

    with pytest.raises(ValueError, match="strict"):
        decision_pipeline_pkg.create_decision_pipeline(strict=2)  # type: ignore[arg-type]


def test_package_factory_accepts_bytes_for_risk_threshold_and_strict(monkeypatch):
    sentinel = object()

    def _fake_create(**kwargs):
        assert kwargs["risk_threshold"] == 0.55
        assert kwargs["strict"] is True
        return sentinel

    monkeypatch.setattr(decision_pipeline_pkg.DecisionPipelineEngine, "create", _fake_create)
    built = decision_pipeline_pkg.create_decision_pipeline(
        risk_threshold=b"0.55",
        strict=b"1",
    )
    assert built is sentinel
