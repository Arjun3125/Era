"""Tests for prime decision engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from core.contracts import DecisionContract, ExecutionContext, InputContract
from modules.prime_decision.engine import PrimeDecisionEngine, PrimeDecisionResult
from modules.prime_decision.module import PrimeDecisionModule


@dataclass
class _MinisterObject:
    stance: str = "accept_with_mitigation"
    confidence: str = "nan"
    reasoning: str = "risk-managed"
    red_line_triggered: str = "yes"


class _PrimeStub:
    def __init__(self):
        self.last_call = None

    def decide(self, council_payload, minister_outputs):
        self.last_call = (dict(council_payload), dict(minister_outputs))
        return {
            "final_outcome": "accept",
            "reason": "stub_accept",
            "confidence": 0.9,
        }


class _PrimeExploding:
    def decide(self, council_payload, minister_outputs):
        raise RuntimeError("prime blew up")


class _PartialRedLineIterable:
    def __iter__(self):
        yield "Risk"
        raise RuntimeError("redline-iter-failed")


class _PartialMinisterIterable:
    def __iter__(self):
        yield {
            "minister": "Risk",
            "stance": "support",
            "confidence": "0.6",
            "reasoning": "bounded",
        }
        raise RuntimeError("minister-iter-failed")


def test_prime_engine_normalizes_minister_object_payloads():
    prime = _PrimeStub()
    engine = PrimeDecisionEngine(prime_decider=prime)

    result = engine.evaluate(
        council_recommendation={
            "outcome": "consensus_reached",
            "recommendation": "support",
            "consensus_strength": 0.7,
            "mode": "meeting",
        },
        minister_outputs={"risk": _MinisterObject()},
        mode="meeting",
        context={"x": 1},
    )

    normalized = result.normalized_minister_outputs["risk"]
    assert normalized["stance"] == "support"
    assert normalized["confidence"] == 0.0
    assert normalized["red_line_triggered"] is True
    assert result.final_decision["final_outcome"] == "accept"
    assert result.decision_contract.confidence == 0.9


def test_prime_engine_quick_bypass_and_redline_string_normalization():
    engine = PrimeDecisionEngine(prime_decider=_PrimeExploding())

    result = engine.evaluate(
        council_recommendation={
            "outcome": "quick_mode_direct_response",
            "recommendation": "use_direct_llm_response",
            "red_line_concerns": "Risk,Truth",
        },
        minister_outputs=None,
        mode="quick_mode",
        context={},
    )

    assert result.final_decision["final_outcome"] == "direct_response"
    assert result.final_decision["reason"] == "quick_mode_bypass"
    assert result.normalized_council["red_line_concerns"] == ["risk", "truth"]
    assert result.decision_contract.mode == "quick"


def test_prime_engine_accepts_bytes_payload_and_iterable_ministers():
    engine = PrimeDecisionEngine(prime_decider=_PrimeStub())

    result = engine.evaluate(
        council_recommendation=b'{"outcome":"consensus_reached","recommendation":"support","consensus_strength":"0.8","mode":"meeting"}',
        minister_outputs=(item for item in [{"minister": "Risk", "stance": "accept", "confidence": "0.6", "red_line_triggered": 2}]),
        mode=b"meeting",
        context={},
    )

    assert result.normalized_minister_outputs["risk"]["stance"] == "support"
    assert result.normalized_minister_outputs["risk"]["red_line_triggered"] is False
    assert result.final_decision["final_outcome"] == "accept"


def test_prime_engine_accepts_iterable_kv_council_and_ministers():
    engine = PrimeDecisionEngine(prime_decider=_PrimeStub())

    result = engine.evaluate(
        council_recommendation=[
            ("outcome", "consensus_reached"),
            ("recommendation", "support"),
            ("consensus_strength", "0.7"),
            ("mode", "meeting"),
        ],
        minister_outputs=[
            (
                "Risk",
                [
                    ("stance", "accept_with_mitigation"),
                    ("confidence", "0.4"),
                    ("reasoning", "bounded"),
                    ("red_line_triggered", "false"),
                ],
            )
        ],
        mode="meeting",
        context={},
    )

    assert result.normalized_council["recommendation"] == "support"
    assert result.normalized_minister_outputs["risk"]["stance"] == "support"
    assert result.normalized_minister_outputs["risk"]["confidence"] == 0.4
    assert result.final_decision["final_outcome"] == "accept"


def test_prime_engine_preserves_partial_iterables_for_redlines_and_ministers():
    engine = PrimeDecisionEngine(prime_decider=_PrimeStub())

    result = engine.evaluate(
        council_recommendation={
            "outcome": "consensus_reached",
            "recommendation": "support",
            "red_line_concerns": _PartialRedLineIterable(),
            "mode": "meeting",
        },
        minister_outputs=_PartialMinisterIterable(),
        mode="meeting",
        context={},
    )

    assert result.normalized_council["red_line_concerns"] == ["risk"]
    assert result.normalized_minister_outputs["risk"]["confidence"] == 0.6
    assert any("partial" in warning.lower() for warning in result.warnings)


def test_prime_engine_falls_back_when_prime_decider_raises():
    engine = PrimeDecisionEngine(prime_decider=_PrimeExploding())

    result = engine.evaluate(
        council_recommendation={
            "outcome": "consensus_reached",
            "recommendation": "support",
            "consensus_strength": 0.8,
            "mode": "meeting",
        },
        minister_outputs={"risk": {"stance": "support", "confidence": 0.7}},
        mode="meeting",
        context={},
    )

    assert result.final_decision["final_outcome"] == "defer"
    assert result.final_decision["reason"] == "prime_decider_exception"
    assert result.decision_contract.decision == "defer"
    assert any("Prime decider failed" in warning for warning in result.warnings)


@dataclass
class _ModuleEngineStub:
    def evaluate(self, **kwargs):
        return PrimeDecisionResult(
            final_decision={"final_outcome": "accept", "reason": "ok", "confidence": 0.8},
            decision_contract=DecisionContract(
                decision="accept",
                confidence=0.8,
                rationale="ok",
                mode="meeting",
            ),
            normalized_council={"outcome": "consensus_reached"},
            normalized_minister_outputs={"risk": {"stance": "support", "confidence": 0.8}},
            warnings=[],
        )


@dataclass
class _ModuleEngineExploding:
    risk_threshold: float = 0.7

    def evaluate(self, **kwargs):
        raise RuntimeError("module-eval-failed")


@dataclass
class _ModuleEngineMalformed:
    risk_threshold: float = 0.7

    def evaluate(self, **kwargs):
        return {
            "final_decision": {"final_outcome": "accept", "confidence": "nan"},
            "decision_contract": "bad-contract",
            "normalized_council": "bad-council",
            "normalized_minister_outputs": {"Risk": {"stance": "support", "confidence": "1.4"}},
            "warnings": "legacy-warning",
        }


def test_prime_module_source_precedence_and_fallback():
    module_ok = PrimeDecisionModule(engine=_ModuleEngineStub())
    context_ok = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "resolved_mode": "meeting",
            "council_result_normalized": {"outcome": "consensus_reached"},
            "minister_outputs_normalized": {"risk": {"stance": "support", "confidence": 0.7}},
        },
    )

    result_ok = module_ok.execute(context_ok)
    assert result_ok.status.value == "success"
    assert result_ok.outputs["prime_decision_source"] == "state.council_result_normalized"
    assert result_ok.outputs["prime_minister_source"] == "state.minister_outputs_normalized"

    module_bad = PrimeDecisionModule(engine=_ModuleEngineExploding())
    context_bad = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"council_result": {"outcome": "deadlocked", "recommendation": "defer"}},
    )

    result_bad = module_bad.execute(context_bad)
    assert result_bad.status.value == "degraded"
    assert result_bad.outputs["prime_decision"]["final_outcome"] == "defer"
    assert result_bad.outputs["decision_contract"].decision == "defer"
    assert any("RuntimeError" in err for err in result_bad.errors)


def test_prime_module_normalizes_malformed_engine_payload():
    module = PrimeDecisionModule(engine=_ModuleEngineMalformed())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"council_result": {"outcome": "deadlocked", "recommendation": "defer"}},
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    assert result.outputs["prime_decision"]["final_outcome"] == "accept"
    assert result.outputs["prime_decision"]["confidence"] == 0.0
    assert result.outputs["decision_contract"].mode == "meeting"
    assert result.outputs["prime_normalized_minister_outputs"]["risk"]["confidence"] == 1.0
    assert "legacy-warning" in result.outputs["prime_decision_warnings"]


def test_prime_module_reads_normalized_context_and_engine_field_keys():
    @dataclass
    class _ModuleEngineVariantMalformed:
        risk_threshold: float = 0.7

        def evaluate(self, **kwargs):
            return {
                "final-decision": {"final_outcome": "accept", "confidence": "0.5", "reason": "ok"},
                "decision-contract": DecisionContract(
                    decision="accept",
                    confidence=0.5,
                    rationale="ok",
                    mode="war",
                ),
                "normalized-council": {"outcome": "consensus_reached"},
                "normalized-minister-outputs": {"Risk": {"stance": "support", "confidence": "0.9"}},
                "warnings": (item for item in ["warn", "warn"]),
            }

    module = PrimeDecisionModule(engine=_ModuleEngineVariantMalformed())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x", metadata={"requested-mode": "war"}),
        state={"council-result": {"outcome": "deadlocked", "recommendation": "defer"}},
    )

    result = module.execute(context)
    assert result.outputs["prime_decision"]["mode"] == "war"
    assert result.outputs["prime_normalized_minister_outputs"]["risk"]["confidence"] == 0.9
    assert result.outputs["prime_decision_warnings"] == ["warn"]


def test_prime_module_accepts_iterable_state_and_iterable_engine_result():
    @dataclass
    class _ModuleEngineIterableResult:
        risk_threshold: float = 0.7

        def evaluate(self, **kwargs):
            return [
                ("final-decision", [("final_outcome", "accept"), ("confidence", "0.8"), ("reason", "ok")]),
                (
                    "decision-contract",
                    DecisionContract(
                        decision="accept",
                        confidence=0.8,
                        rationale="ok",
                        mode="war",
                    ),
                ),
                ("normalized-council", [("outcome", "consensus_reached"), ("mode", "war")]),
                ("normalized-minister-outputs", [("Risk", [("stance", "support"), ("confidence", "0.5")])]),
                ("warnings", ["iter-warn", "iter-warn"]),
            ]

    module = PrimeDecisionModule(engine=_ModuleEngineIterableResult())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "council_result": [("outcome", "deadlocked"), ("recommendation", "defer"), ("mode", "war")],
        },
    )

    result = module.execute(context)
    assert result.outputs["prime_decision"]["mode"] == "war"
    assert result.outputs["prime_normalized_minister_outputs"]["risk"]["confidence"] == 0.5
    assert result.outputs["prime_decision_warnings"] == ["iter-warn"]


def test_prime_module_preserves_partial_iterable_engine_payload():
    class _PartialWarnings:
        def __iter__(self):
            yield "warn-a"
            yield "warn-b"
            raise RuntimeError("warnings-iter-failed")

    class _PartialPayload(Mapping):
        def __getitem__(self, key):
            data = {
                "final-decision": [
                    ("final_outcome", "accept"),
                    ("confidence", "0.8"),
                    ("reason", "ok"),
                    ("mode", "war"),
                ],
                "normalized-council": [("outcome", "consensus_reached"), ("mode", "war")],
                "normalized-minister-outputs": [
                    ("Risk", [("stance", "support"), ("confidence", "0.5")])
                ],
                "warnings": _PartialWarnings(),
            }
            return data[key]

        def __iter__(self):
            yield "final-decision"
            yield "normalized-council"
            yield "normalized-minister-outputs"
            yield "warnings"
            raise RuntimeError("payload-iter-failed")

        def __len__(self) -> int:
            return 4

        def items(self):
            yield (
                "final-decision",
                [
                    ("final_outcome", "accept"),
                    ("confidence", "0.8"),
                    ("reason", "ok"),
                    ("mode", "war"),
                ],
            )
            yield ("normalized-council", [("outcome", "consensus_reached"), ("mode", "war")])
            yield (
                "normalized-minister-outputs",
                [("Risk", [("stance", "support"), ("confidence", "0.5")])],
            )
            yield ("warnings", _PartialWarnings())
            raise RuntimeError("payload-items-failed")

    @dataclass
    class _PartialEngine:
        risk_threshold: float = 0.7

        def evaluate(self, **kwargs):
            return _PartialPayload()

    module = PrimeDecisionModule(engine=_PartialEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "council_result": {"outcome": "deadlocked", "recommendation": "defer", "mode": "war"},
        },
    )

    result = module.execute(context)

    assert result.outputs["prime_decision"]["mode"] == "war"
    assert result.outputs["prime_normalized_minister_outputs"]["risk"]["confidence"] == 0.5
    assert result.outputs["prime_decision_warnings"] == ["warn-a", "warn-b"]
