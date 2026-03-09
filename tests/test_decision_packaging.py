"""Tests for decision packaging engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json

from core.contracts import (
    DecisionContract,
    DecisionPackagingContract,
    ExecutionContext,
    InputContract,
)
from modules.decision_packaging.engine import DecisionPackagingEngine
from modules.decision_packaging.module import DecisionPackagingModule


@dataclass
class _PrimeObject:
    final_outcome: str = "yes"
    reason: str = "   "
    confidence: str = "nan"


@dataclass
class _CouncilObject:
    recommendation: str = "unknown"
    outcome: str = "mystery"
    red_line_concerns: object = None
    requires_followup: str = "off"


@dataclass
class _KnowledgeObject:
    synthesized_knowledge: str = "fact-a"


class _ExplodingEngine:
    def package(self, **kwargs):
        raise RuntimeError("packaging boom")


class _MalformedPackagingEngine:
    def package(self, **kwargs):
        return {
            "package": {
                "final_outcome": "accept",
                "confidence": "nan",
                "red_line_concerns": ["Risk", "risk"],
                "knowledge_items_used": "nan",
                "requires_followup": "yes",
            },
            "contract": "invalid-contract",
            "warnings": "legacy-warning",
        }


class _FaultyPrimeMapping(Mapping):
    def __getitem__(self, key):
        if key == "final_outcome":
            return "accept"
        raise KeyError(key)

    def __iter__(self):
        yield "final_outcome"
        raise RuntimeError("prime-iter-failed")

    def __len__(self):
        return 1

    def items(self):
        yield ("final_outcome", "accept")
        raise RuntimeError("prime-items-failed")


class _FaultyRedLineIterable:
    def __iter__(self):
        yield "Risk"
        raise RuntimeError("redline-iter-failed")


class _FaultyKnowledgeIterable:
    def __iter__(self):
        yield "fact-a"
        raise RuntimeError("knowledge-iter-failed")


class _PartialWarningIterable:
    def __iter__(self):
        yield "warn-a"
        yield "warn-b"
        raise RuntimeError("warning-iter-failed")


class _PartialPackagingPayload(Mapping):
    def __getitem__(self, key):
        data = {
            "package": [
                ("final_outcome", "accept"),
                ("reason", "ok"),
                ("mode", "meeting"),
            ],
            "warnings": _PartialWarningIterable(),
        }
        return data[key]

    def __iter__(self):
        yield "package"
        yield "warnings"
        raise RuntimeError("payload-iter-failed")

    def __len__(self):
        return 2

    def items(self):
        yield ("package", [("final_outcome", "accept"), ("reason", "ok"), ("mode", "meeting")])
        yield ("warnings", _PartialWarningIterable())
        raise RuntimeError("payload-items-failed")


def test_decision_packaging_engine_normalizes_aliases_and_derives_followup():
    engine = DecisionPackagingEngine()

    result = engine.package(
        decision_contract=DecisionContract(decision="accept", confidence=0.2, rationale="", mode="meeting"),
        prime_decision={
            "final_outcome": "accept_with_mitigation",
            "reason": "",
            "confidence": "1.4",
        },
        council_result={
            "recommendation": "accept_with_mitigation",
            "outcome": "balanced",
            "red_line_concerns": "Risk, risk",
        },
        knowledge_result={"synthesized_items": ["item-a", "item-a", "item-b"]},
        mode="quick_mode",
    )

    assert result.package["final_outcome"] == "accept_with_mitigation"
    assert result.package["recommendation"] == "support"
    assert result.package["council_outcome"] == "bounded_risk_tradeoff"
    assert result.package["mode"] == "quick"
    assert result.package["confidence"] == 1.0
    assert result.package["reason"] == "decision_reason_unavailable"
    assert result.package["red_line_concerns"] == ["risk"]
    assert result.package["knowledge_items_used"] == 2
    assert result.package["requires_followup"] is True
    assert result.contract.warning_count == len(result.warnings)


def test_decision_packaging_engine_supports_object_payloads_and_invalid_values():
    engine = DecisionPackagingEngine()

    result = engine.package(
        decision_contract=None,
        prime_decision=_PrimeObject(),
        council_result=_CouncilObject(red_line_concerns={"risk": True}),
        knowledge_result=_KnowledgeObject(),
        mode="unknown_mode",
    )

    assert result.package["final_outcome"] == "accept"
    assert result.package["recommendation"] == "defer"
    assert result.package["council_outcome"] == "not_invoked"
    assert result.package["mode"] == "meeting"
    assert result.package["confidence"] == 0.0
    assert result.package["red_line_concerns"] == []
    assert result.package["knowledge_items_used"] == 1
    assert result.package["requires_followup"] is False
    assert any("Unsupported recommendation" in warning for warning in result.warnings)
    assert any("Unsupported council_outcome" in warning for warning in result.warnings)


def test_decision_packaging_module_resolves_sources_and_emits_contract():
    module = DecisionPackagingModule.create()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "decision_contract": DecisionContract(
                decision="accept",
                confidence=0.8,
                rationale="from_contract",
                mode="meeting",
            ),
            "prime_decision": {
                "final_outcome": "accept",
                "reason": "prime_ok",
                "confidence": 0.9,
            },
            "council_result": {
                "outcome": "deadlocked",
                "recommendation": "defer",
                "red_line_concerns": ["risk"],
            },
            "council_result_normalized": {
                "outcome": "consensus_reached",
                "recommendation": "support",
                "red_line_concerns": [],
            },
            "knowledge_result": {"synthesized_knowledge": ["fact-a"]},
            "resolved_mode": "meeting",
        },
    )

    result = module.execute(context)
    assert result.status.value == "success"
    assert result.outputs["decision_package"]["recommendation"] == "support"
    assert result.outputs["decision_package"]["council_outcome"] == "consensus_reached"

    sources = result.outputs["decision_packaging_sources"]
    assert sources["decision_contract"] == "state.decision_contract"
    assert sources["prime_decision"] == "state.prime_decision"
    assert sources["council_result"] == "state.council_result_normalized"
    assert sources["knowledge_result"] == "state.knowledge_result"


def test_decision_packaging_module_degrades_on_engine_failure():
    module = DecisionPackagingModule(engine=_ExplodingEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "decision_contract": DecisionContract(decision="accept"),
            "prime_decision": {"final_outcome": "accept"},
            "requested_mode": "meeting",
        },
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    assert result.outputs["decision_package"]["final_outcome"] == "defer"
    assert result.outputs["decision_packaging_contract"].source == "decision_packaging.module.exception"
    assert result.outputs["decision_packaging_contract"].requires_followup is True
    assert any("RuntimeError" in err for err in result.errors)


def test_decision_packaging_module_normalizes_malformed_engine_payload():
    module = DecisionPackagingModule(engine=_MalformedPackagingEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"decision_contract": DecisionContract(decision="accept"), "requested_mode": "meeting"},
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    assert result.outputs["decision_package"]["final_outcome"] == "accept"
    assert result.outputs["decision_package"]["confidence"] == 0.0
    assert result.outputs["decision_package"]["red_line_concerns"] == ["risk"]
    assert result.outputs["decision_package"]["knowledge_items_used"] == 0
    assert result.outputs["decision_package"]["requires_followup"] is True
    assert isinstance(result.outputs["decision_packaging_contract"], DecisionPackagingContract)
    assert "legacy-warning" in result.errors


def test_decision_packaging_engine_supports_json_iterable_payloads_and_strict_followup_bool():
    engine = DecisionPackagingEngine()

    result = engine.package(
        decision_contract=DecisionContract(decision="accept", confidence=0.3, mode="meeting"),
        prime_decision=json.dumps(
            {
                "final-outcome": "accept",
                "reason": "json-prime",
                "confidence": "0.73",
                "requires-followup": 2,
            }
        ),
        council_result=[
            ("recommendation", "support"),
            ("outcome", "consensus_reached"),
            ("red-line-concerns", b""),
        ],
        knowledge_result=json.dumps({"synthesized-knowledge": ["fact-a", "fact-a"]}),
        mode=b"meeting",
    )

    assert result.package["final_outcome"] == "accept"
    assert result.package["confidence"] == 0.73
    assert result.package["knowledge_items_used"] == 1
    assert result.package["requires_followup"] is False


def test_decision_packaging_engine_accepts_json_array_of_kv_pairs():
    engine = DecisionPackagingEngine()

    result = engine.package(
        decision_contract=DecisionContract(decision="accept", confidence=0.3, mode="meeting"),
        prime_decision='[["final_outcome","accept"],["reason","json-array"],["confidence","0.6"],["mode","war"]]',
        council_result='[["recommendation","support"],["outcome","consensus_reached"],["red_line_concerns",["risk"]]]',
        knowledge_result='[["synthesized_knowledge",["fact-a","fact-b"]]]',
        mode="war",
    )

    assert result.package["final_outcome"] == "accept"
    assert result.package["mode"] == "war"
    assert result.package["knowledge_items_used"] == 2
    assert result.package["red_line_concerns"] == ["risk"]


def test_decision_packaging_engine_preserves_partial_mapping_and_iterable_values():
    engine = DecisionPackagingEngine()

    result = engine.package(
        decision_contract=DecisionContract(decision="defer", confidence=0.3, mode="meeting"),
        prime_decision=_FaultyPrimeMapping(),
        council_result={
            "recommendation": "support",
            "outcome": "consensus_reached",
            "red_line_concerns": _FaultyRedLineIterable(),
        },
        knowledge_result={"synthesized_knowledge": _FaultyKnowledgeIterable()},
        mode="meeting",
    )

    assert result.package["final_outcome"] == "accept"
    assert result.package["red_line_concerns"] == ["risk"]
    assert result.package["knowledge_items_used"] == 1
    assert any("partial" in warning.lower() for warning in result.warnings)


def test_decision_packaging_module_reads_normalized_state_keys():
    module = DecisionPackagingModule.create()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "decision-contract": DecisionContract(decision="accept", confidence=0.6, mode="meeting"),
            "prime-decision": {
                "final-outcome": "accept",
                "reason": "from-prime",
                "confidence": 0.9,
            },
            "council-result-normalized": {
                "recommendation": "support",
                "outcome": "consensus_reached",
                "red-line-concerns": b"risk",
            },
            "knowledge-result": {"synthesized-knowledge": ["fact-a"]},
            "resolved-mode": "meeting",
        },
    )

    result = module.execute(context)
    assert result.status.value == "success"
    assert result.outputs["decision_package"]["red_line_concerns"] == ["risk"]
    assert result.outputs["decision_packaging_sources"]["decision_contract"] == "state.decision_contract"
    assert result.outputs["decision_packaging_sources"]["prime_decision"] == "state.prime_decision"


def test_decision_packaging_module_accepts_iterable_prime_mode_and_engine_payload():
    class _IterablePackagingEngine:
        def package(self, **kwargs):
            return [
                (
                    "package",
                    [
                        ("final_outcome", "accept"),
                        ("reason", "ok"),
                        ("confidence", "0.7"),
                        ("mode", "war"),
                        ("recommendation", "support"),
                        ("council_outcome", "consensus_reached"),
                        ("red_line_concerns", ["risk"]),
                        ("knowledge_items_used", "2"),
                        ("requires_followup", "false"),
                    ],
                ),
                ("warnings", ["iter-warn", "iter-warn"]),
            ]

    module = DecisionPackagingModule(engine=_IterablePackagingEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "decision_contract": DecisionContract(decision="accept", mode="meeting"),
            "prime_decision": [("mode", "war"), ("final_outcome", "accept")],
        },
    )

    result = module.execute(context)
    assert result.outputs["decision_package"]["mode"] == "war"
    assert result.outputs["decision_package"]["knowledge_items_used"] == 2
    assert result.errors == ["iter-warn"]


def test_decision_packaging_module_preserves_partial_iterable_packaging_payload():
    class _PartialPackagingEngine:
        def package(self, **kwargs):
            return _PartialPackagingPayload()

    module = DecisionPackagingModule(engine=_PartialPackagingEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"decision_contract": DecisionContract(decision="accept", mode="meeting")},
    )

    result = module.execute(context)
    assert result.outputs["decision_package"]["final_outcome"] == "accept"
    assert result.outputs["decision_package"]["reason"] == "ok"
    assert result.errors == ["warn-a", "warn-b"]
