"""Tests for contract validation engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

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
    RequestContextContract,
    RuntimeConfigContract,
)
from modules.contract_validation.engine import ContractValidationEngine
from modules.contract_validation.module import ContractValidationModule


class _FaultyDecisionPackage(Mapping):
    def __getitem__(self, key):
        data = {
            "final_outcome": "accept",
            "mode": "meeting",
            "confidence": 0.82,
            "recommendation": "support",
            "council_outcome": "consensus_reached",
            "red_line_concerns": [],
            "knowledge_items_used": 1,
            "requires_followup": False,
        }
        return data[key]

    def __iter__(self):
        yield "final_outcome"
        yield "mode"
        yield "confidence"
        yield "recommendation"
        yield "council_outcome"
        yield "red_line_concerns"
        yield "knowledge_items_used"
        yield "requires_followup"
        raise RuntimeError("decision-package-iter-failed")

    def __len__(self):
        return 8

    def items(self):
        yield ("final_outcome", "accept")
        yield ("mode", "meeting")
        yield ("confidence", 0.82)
        yield ("recommendation", "support")
        yield ("council_outcome", "consensus_reached")
        yield ("red_line_concerns", [])
        yield ("knowledge_items_used", 1)
        yield ("requires_followup", False)
        raise RuntimeError("decision-package-items-failed")


class _FaultyDomainIterable:
    def __iter__(self):
        yield "strategy"
        raise RuntimeError("domains-iter-failed")


class _FaultyMinisterIterable:
    def __iter__(self):
        yield "risk"
        raise RuntimeError("ministers-iter-failed")


def _build_valid_state() -> dict:
    return {
        "request_context_contract": RequestContextContract(
            requested_mode="meeting",
            routing_context={"domains": ["strategy"]},
            warning_count=0,
        ),
        "runtime_config_contract": RuntimeConfigContract(decision_pipeline_enabled=True),
        "mode_contract": ModeResolutionContract(
            mode="meeting",
            should_invoke_council=True,
            selected_ministers=["risk"],
            rationale="council required",
            confidence=0.9,
        ),
        "domain_analysis_contract": DomainAnalysisContract(
            domains=["strategy", "finance"],
            domain_confidence=0.7,
            stakes="high",
            reversibility="partially_reversible",
        ),
        "knowledge_contract": KnowledgeContract(
            active_domains=["strategy"],
            synthesized_items=["fact-a"],
            trace=[],
            quality={},
        ),
        "council_contract": CouncilContract(
            outcome="consensus_reached",
            recommendation="support",
            consensus_strength=0.8,
            minister_positions={"risk": {"stance": "support"}},
            red_line_concerns=[],
        ),
        "council_normalization_contract": CouncilNormalizationContract(
            mode="meeting",
            outcome="consensus_reached",
            recommendation="support",
            consensus_strength=0.8,
            minister_count=1,
            failed_minister_count=0,
            red_line_count=0,
            council_invoked=True,
            warning_count=0,
        ),
        "decision_contract": DecisionContract(
            decision="accept",
            confidence=0.82,
            rationale="aligned",
            mode="meeting",
        ),
        "decision_packaging_contract": DecisionPackagingContract(
            final_outcome="accept",
            mode="meeting",
            confidence=0.82,
            recommendation="support",
            council_outcome="consensus_reached",
            red_line_count=0,
            knowledge_item_count=1,
            requires_followup=False,
            warning_count=0,
        ),
        "decision_package": {
            "final_outcome": "accept",
            "mode": "meeting",
            "confidence": 0.82,
            "recommendation": "support",
            "council_outcome": "consensus_reached",
            "red_line_concerns": [],
            "knowledge_items_used": 1,
            "requires_followup": False,
        },
        "routing_context": {"domains": ["strategy"]},
    }


def test_contract_validation_engine_passes_for_aligned_contracts():
    engine = ContractValidationEngine()
    result = engine.validate(state=_build_valid_state())

    assert result.contract.passed is True
    assert result.contract.error_count == 0
    assert result.contract.warning_count == 0
    assert result.checks["decision_package_outcome_alignment"] == "pass"
    assert result.checks["decision_package_confidence_alignment"] == "pass"


def test_contract_validation_engine_reports_cross_contract_warnings():
    engine = ContractValidationEngine()
    state = _build_valid_state()

    state["runtime_config_contract"] = RuntimeConfigContract(decision_pipeline_enabled=False)
    state["mode_contract"] = ModeResolutionContract(
        mode="meeting",
        should_invoke_council=True,
        selected_ministers=[],
        rationale="",
        confidence=0.5,
    )
    state["council_normalization_contract"] = CouncilNormalizationContract(
        mode="war",
        outcome="deadlocked",
        recommendation="defer",
        consensus_strength=0.2,
        minister_count=1,
        failed_minister_count=0,
        red_line_count=0,
        council_invoked=True,
        warning_count=0,
    )
    state["decision_package"] = {
        "final_outcome": "reject",
        "mode": "quick",
        "confidence": "nan",
        "recommendation": "oppose",
        "council_outcome": "deadlocked",
        "red_line_concerns": "risk",
        "knowledge_items_used": "x",
        "requires_followup": True,
    }

    result = engine.validate(state=state)
    assert result.contract.passed is True
    assert result.contract.error_count == 0
    assert result.contract.warning_count > 0
    assert "runtime_pipeline_enabled" in result.contract.warning_checks
    assert "council_readiness" in result.contract.warning_checks
    assert "decision_package_outcome_alignment" in result.contract.warning_checks
    assert "decision_package_mode_alignment" in result.contract.warning_checks
    assert "decision_confidence_range" in result.contract.warning_checks


def test_contract_validation_module_fails_when_required_contracts_missing():
    module = ContractValidationModule.create()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={},
    )

    result = module.execute(context)
    assert result.status.value == "failed"
    assert result.outputs["contract_validation_contract"].passed is False
    assert result.outputs["contract_validation_contract"].error_count > 0
    assert result.outputs["contract_validation_sources"]["decision_contract"] is False


@dataclass
class _ExplodingEngine:
    def validate(self, *, state):
        raise RuntimeError("validation boom")


@dataclass
class _MalformedEngine:
    def validate(self, *, state):
        return {
            "contract": "bad-contract",
            "issues": "legacy-issue",
            "checks": "bad-checks",
        }


def test_contract_validation_module_degrades_on_engine_exception():
    module = ContractValidationModule(engine=_ExplodingEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"decision_contract": DecisionContract(decision="accept")},
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    contract = result.outputs["contract_validation_contract"]
    assert isinstance(contract, ContractValidationContract)
    assert contract.source == "contract_validation.module.exception"
    assert contract.error_count == 1
    assert any("RuntimeError" in err for err in result.errors)


def test_contract_validation_module_normalizes_malformed_engine_payload():
    module = ContractValidationModule(engine=_MalformedEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"decision_contract": DecisionContract(decision="accept")},
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    contract = result.outputs["contract_validation_contract"]
    assert isinstance(contract, ContractValidationContract)
    assert contract.warning_count >= 1
    assert "legacy-issue" in result.outputs["contract_validation_issues"]


def test_contract_validation_engine_accepts_normalized_state_and_package_keys():
    engine = ContractValidationEngine()
    state = _build_valid_state()

    state = {key.replace("_", "-"): value for key, value in state.items()}
    state["decision-package"] = {
        "final-outcome": "accept",
        "mode": "meeting",
        "confidence": "0.82",
        "recommendation": "support",
        "council-outcome": "consensus_reached",
        "red-line-concerns": {"risk": True},
        "knowledge-items-used": "1",
        "requires-followup": "0",
    }
    state["routing-context"] = {"domains": ["strategy"]}
    state["decision-packaging-contract"].red_line_count = 1

    result = engine.validate(state=state)
    assert result.contract.passed is True
    assert result.checks["decision_package_outcome_alignment"] == "pass"
    assert result.checks["decision_package_followup_alignment"] == "pass"
    assert result.checks["decision_package_red_line_count_alignment"] == "pass"


def test_contract_validation_engine_parses_string_followup_bool_without_false_warning():
    engine = ContractValidationEngine()
    state = _build_valid_state()
    state["decision_package"]["requires_followup"] = "false"
    state["decision_packaging_contract"] = DecisionPackagingContract(
        final_outcome="accept",
        mode="meeting",
        confidence=0.82,
        recommendation="support",
        council_outcome="consensus_reached",
        red_line_count=0,
        knowledge_item_count=1,
        requires_followup=False,
        warning_count=0,
    )

    result = engine.validate(state=state)
    assert "decision_package_followup_alignment" not in result.contract.warning_checks


def test_contract_validation_module_tracks_normalized_source_keys():
    module = ContractValidationModule.create()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "decision-contract": DecisionContract(decision="accept"),
            "decision-package": {"final-outcome": "accept"},
        },
    )

    result = module.execute(context)
    sources = result.outputs["contract_validation_sources"]
    assert sources["decision_contract"] is True
    assert sources["decision_package"] is True


def test_contract_validation_engine_accepts_json_mapping_payloads():
    engine = ContractValidationEngine()
    state = _build_valid_state()

    state["decision_package"] = json.dumps(
        {
            "final_outcome": "accept",
            "mode": "meeting",
            "confidence": 0.82,
            "recommendation": "support",
            "council_outcome": "consensus_reached",
            "red_line_concerns": [],
            "knowledge_items_used": 1,
            "requires_followup": False,
        }
    )
    state["routing_context"] = json.dumps({"domains": ["strategy"]})

    result = engine.validate(state=state)
    assert result.checks["decision_package_type"] == "pass"
    assert result.checks["routing_context_type"] == "pass"


def test_contract_validation_engine_preserves_partial_iterable_state_values():
    engine = ContractValidationEngine()
    state = _build_valid_state()

    state["domain_analysis_contract"] = DomainAnalysisContract(
        domains=_FaultyDomainIterable(),  # type: ignore[arg-type]
        domain_confidence=0.7,
        stakes="high",
        reversibility="partially_reversible",
    )
    state["mode_contract"] = ModeResolutionContract(
        mode="meeting",
        should_invoke_council=True,
        selected_ministers=_FaultyMinisterIterable(),  # type: ignore[arg-type]
        rationale="council required",
        confidence=0.9,
    )
    state["decision_package"] = _FaultyDecisionPackage()  # type: ignore[assignment]

    result = engine.validate(state=state)
    assert result.contract.passed is True
    assert result.checks["domain_non_empty"] == "pass"
    assert result.checks["council_readiness"] == "pass"
    assert result.checks["decision_package_outcome_alignment"] == "pass"


def test_contract_validation_module_preserves_partial_iterable_engine_payload():
    class _PartialIssues:
        def __iter__(self):
            yield "warn-a"
            yield "warn-b"
            raise RuntimeError("issues-iter-failed")

    class _PartialPayload(Mapping):
        def __getitem__(self, key):
            data = {
                "contract": ContractValidationContract(
                    passed=True,
                    warning_count=1,
                    error_count=0,
                    warning_checks=["shape_warning"],
                    failed_checks=[],
                    checks={"shape_warning": "warning"},
                    source="stub",
                ),
                "issues": _PartialIssues(),
                "checks": [("shape_warning", "warning"), ("alignment", "pass")],
            }
            return data[key]

        def __iter__(self):
            yield "contract"
            yield "issues"
            yield "checks"
            raise RuntimeError("payload-iter-failed")

        def __len__(self) -> int:
            return 3

        def items(self):
            yield (
                "contract",
                ContractValidationContract(
                    passed=True,
                    warning_count=1,
                    error_count=0,
                    warning_checks=["shape_warning"],
                    failed_checks=[],
                    checks={"shape_warning": "warning"},
                    source="stub",
                ),
            )
            yield ("issues", _PartialIssues())
            yield ("checks", [("shape_warning", "warning"), ("alignment", "pass")])
            raise RuntimeError("payload-items-failed")

    @dataclass
    class _PartialEngine:
        def validate(self, *, state):
            _ = state
            return _PartialPayload()

    module = ContractValidationModule(engine=_PartialEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"decision_contract": DecisionContract(decision="accept")},
    )

    result = module.execute(context)

    assert result.outputs["contract_validation_issues"] == ["warn-a", "warn-b"]
    assert result.outputs["contract_validation_checks"]["shape_warning"] == "warning"
    assert result.outputs["contract_validation_checks"]["alignment"] == "pass"
