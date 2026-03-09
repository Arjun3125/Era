"""Tests for council normalization engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from core.contracts import (
    CouncilContract,
    CouncilNormalizationContract,
    ExecutionContext,
    InputContract,
)
from modules.council_normalization.engine import CouncilNormalizationEngine
from modules.council_normalization.module import CouncilNormalizationModule


class _FaultyCouncilPayload(Mapping):
    def __getitem__(self, key):
        data = {
            "outcome": "consensus_reached",
            "recommendation": "support",
        }
        return data[key]

    def __iter__(self):
        yield "outcome"
        raise RuntimeError("payload-iter-failed")

    def __len__(self):
        return 2

    def items(self):
        yield ("outcome", "consensus_reached")
        yield ("recommendation", "support")
        raise RuntimeError("payload-items-failed")


class _FaultyRedLineIterable:
    def __iter__(self):
        yield "Risk"
        raise RuntimeError("redline-iter-failed")


class _FaultyMinisterIterable:
    def __iter__(self):
        yield {"minister": "Risk", "stance": "accept", "confidence": "0.6"}
        raise RuntimeError("minister-iter-failed")


def test_council_normalization_engine_maps_quick_response_to_defer_and_not_invoked():
    engine = CouncilNormalizationEngine()

    contract = CouncilContract(
        outcome="quick_mode_direct_response",
        recommendation="use_direct_llm_response",
        consensus_strength=0.4,
        minister_positions={},
        red_line_concerns=[],
    )
    result = engine.normalize(council_result=contract, mode="quick_mode")

    assert result.contract.mode == "quick"
    assert result.contract.outcome == "quick_mode_direct_response"
    assert result.contract.recommendation == "defer"
    assert result.contract.council_invoked is False
    assert result.normalized_council["source_outcome"] == "quick_mode_direct_response"


def test_council_normalization_engine_accepts_json_payload_and_strict_redline_bool():
    engine = CouncilNormalizationEngine()

    result = engine.normalize(
        council_result=b'{"outcome":"balanced","recommendation":"strong_consensus_support","minister_outputs":{"Risk":{"stance":"accept","confidence":"0.8","red_line_triggered":2}}}',
        mode=b"meeting",
    )

    assert result.contract.mode == "meeting"
    assert result.normalized_minister_outputs["risk"]["stance"] == "support"
    assert result.normalized_minister_outputs["risk"]["red_line_triggered"] is False


def test_council_normalization_engine_normalizes_council_positions_list():
    engine = CouncilNormalizationEngine()

    result = engine.normalize(
        council_result={
            "outcome": "balanced",
            "recommendation": "strong_consensus_support",
            "consensus_strength": "1.5",
            "council_positions": [
                {
                    "minister": "Risk",
                    "stance": "accept_with_mitigation",
                    "confidence": "nan",
                    "reasoning": "Test",
                    "red_line": "yes",
                }
            ],
            "ministers_failed": ["risk:RuntimeError", "risk:RuntimeError"],
            "red_line_concerns": ["Risk", "risk"],
        },
        mode="meeting",
    )

    assert result.contract.outcome == "bounded_risk_tradeoff"
    assert result.contract.recommendation == "support"
    assert result.contract.consensus_strength == 1.0

    ministers = result.normalized_minister_outputs
    assert list(ministers.keys()) == ["risk"]
    assert ministers["risk"]["stance"] == "support"
    assert ministers["risk"]["confidence"] == 0.0
    assert ministers["risk"]["red_line_triggered"] is True

    assert result.normalized_council["ministers_failed"] == ["risk:RuntimeError"]
    assert result.normalized_council["red_line_concerns"] == ["risk"]


def test_council_normalization_engine_accepts_iterable_kv_payloads():
    engine = CouncilNormalizationEngine()

    result = engine.normalize(
        council_result=[
            ("outcome", "consensus_reached"),
            ("recommendation", "support"),
            ("mode", "war"),
            (
                "minister_outputs",
                [("Risk", [("stance", "accept"), ("confidence", "0.6"), ("red_line_triggered", "0")])],
            ),
        ],
        mode=None,
    )

    assert result.contract.mode == "war"
    assert result.normalized_minister_outputs["risk"]["stance"] == "support"
    assert result.normalized_minister_outputs["risk"]["confidence"] == 0.6
    assert result.normalized_minister_outputs["risk"]["red_line_triggered"] is False


def test_council_normalization_engine_preserves_partial_payload_and_iterables():
    engine = CouncilNormalizationEngine()

    partial_payload = engine.normalize(council_result=_FaultyCouncilPayload(), mode="meeting")
    assert partial_payload.normalized_council["source_outcome"] == "consensus_reached"
    assert partial_payload.contract.recommendation == "support"

    result = engine.normalize(
        council_result={
            "outcome": "unknown",
            "recommendation": "support",
            "red_line_concerns": _FaultyRedLineIterable(),
            "minister_outputs": _FaultyMinisterIterable(),
        },
        mode="meeting",
    )

    assert result.normalized_council["red_line_concerns"] == ["risk"]
    assert result.normalized_minister_outputs["risk"]["confidence"] == 0.6
    assert result.contract.outcome == "bounded_risk_tradeoff"
    assert any("partial" in warning.lower() for warning in result.warnings)


@dataclass
class _ExplodingNormalizationEngine:
    def normalize(self, **kwargs):
        raise RuntimeError("normalize boom")


def test_council_normalization_module_supports_contract_input_and_degrades_on_failure():
    module_ok = CouncilNormalizationModule.create()
    context_ok = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "council_contract": CouncilContract(
                outcome="council_disabled_ablation",
                recommendation="no_council_response",
                consensus_strength=0.0,
                minister_positions={},
                red_line_concerns=[],
            )
        },
    )

    result_ok = module_ok.execute(context_ok)
    assert result_ok.status.value in {"success", "degraded"}
    assert result_ok.outputs["council_normalization_source"] == "state.council_contract"

    module_bad = CouncilNormalizationModule(engine=_ExplodingNormalizationEngine())
    context_bad = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"council_result": {"outcome": "deadlocked", "recommendation": "defer"}},
    )
    result_bad = module_bad.execute(context_bad)

    assert result_bad.status.value == "degraded"
    assert result_bad.outputs["council_result_normalized"]["outcome"] == "deadlocked"
    assert result_bad.outputs["council_normalization_source"] == "state.council_result"
    assert any("RuntimeError" in err for err in result_bad.errors)


@dataclass
class _MalformedNormalizationPayloadEngine:
    def normalize(self, **kwargs):
        return {
            "normalized_council": "bad-payload",
            "normalized_minister_outputs": {
                "Risk": {
                    "stance": "accept_with_mitigation",
                    "confidence": "nan",
                    "red_line": "yes",
                }
            },
            "warnings": "legacy-warning",
            "contract": "invalid-contract",
        }


def test_council_normalization_module_normalizes_malformed_engine_result():
    module = CouncilNormalizationModule(engine=_MalformedNormalizationPayloadEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"council_result": {"outcome": "deadlocked", "recommendation": "defer"}},
    )

    result = module.execute(context)

    assert result.status.value == "degraded"
    assert result.outputs["council_result_normalized"]["mode"] == "meeting"
    assert isinstance(
        result.outputs["council_normalization_contract"],
        CouncilNormalizationContract,
    )
    assert result.outputs["minister_outputs_normalized"]["risk"]["stance"] == "neutral"
    assert result.outputs["minister_outputs_normalized"]["risk"]["confidence"] == 0.0
    assert "legacy-warning" in result.outputs["council_normalization_warnings"]


def test_council_normalization_module_reads_normalized_state_mode_keys():
    module = CouncilNormalizationModule.create()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x", metadata={"requested-mode": "war"}),
        state={
            "council-result": {
                "outcome": "consensus_reached",
                "recommendation": "support",
                "minister_outputs": {"Risk": {"stance": "support", "confidence": 0.7}},
            }
        },
    )

    result = module.execute(context)
    assert result.outputs["council_result_normalized"]["mode"] == "war"
    assert result.outputs["minister_outputs_normalized"]["risk"]["stance"] == "support"


def test_council_normalization_module_accepts_iterable_state_and_engine_result():
    @dataclass
    class _IterableNormalizationPayloadEngine:
        def normalize(self, **kwargs):
            return [
                ("normalized-council", [("outcome", "consensus_reached"), ("recommendation", "support"), ("mode", "war")]),
                ("normalized-minister-outputs", [("Risk", [("stance", "support"), ("confidence", "0.9")])]),
                ("council-positions", (item for item in [{"minister": "risk", "stance": "support"}])),
                ("warnings", ["iter-warn", "iter-warn"]),
            ]

    module = CouncilNormalizationModule(engine=_IterableNormalizationPayloadEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "council_result": [("mode", "war"), ("outcome", "consensus_reached"), ("recommendation", "support")]
        },  # type: ignore[arg-type]
    )

    result = module.execute(context)
    assert result.outputs["council_result_normalized"]["mode"] == "war"
    assert result.outputs["minister_outputs_normalized"]["risk"]["confidence"] == 0.9
    assert result.outputs["council_normalization_warnings"] == ["iter-warn"]


def test_council_normalization_module_preserves_partial_iterable_engine_payload():
    class _PartialWarnings:
        def __iter__(self):
            yield "warn-a"
            yield "warn-b"
            raise RuntimeError("warn-iter-failed")

    class _PartialPayload(Mapping):
        def __getitem__(self, key):
            data = {
                "normalized-council": [("outcome", "consensus_reached"), ("recommendation", "support")],
                "normalized-minister-outputs": [("Risk", [("stance", "support"), ("confidence", "0.8")])],
                "warnings": _PartialWarnings(),
            }
            return data[key]

        def __iter__(self):
            yield "normalized-council"
            yield "normalized-minister-outputs"
            yield "warnings"
            raise RuntimeError("payload-iter-failed")

        def __len__(self):
            return 3

        def items(self):
            yield ("normalized-council", [("outcome", "consensus_reached"), ("recommendation", "support")])
            yield ("normalized-minister-outputs", [("Risk", [("stance", "support"), ("confidence", "0.8")])])
            yield ("warnings", _PartialWarnings())
            raise RuntimeError("payload-items-failed")

    class _PartialEngine:
        def normalize(self, **kwargs):
            return _PartialPayload()

    module = CouncilNormalizationModule(engine=_PartialEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"council_result": {"outcome": "deadlocked", "recommendation": "defer"}},
    )

    result = module.execute(context)
    assert result.outputs["council_result_normalized"]["outcome"] == "consensus_reached"
    assert result.outputs["minister_outputs_normalized"]["risk"]["confidence"] == 0.8
    assert result.outputs["council_normalization_warnings"] == ["warn-a", "warn-b"]


def test_council_normalization_module_does_not_flag_engine_dataclass_as_malformed():
    module = CouncilNormalizationModule.create()
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={
            "council_result": {
                "outcome": "consensus_reached",
                "recommendation": "support",
                "mode": "meeting",
                "minister_outputs": {
                    "risk": {"stance": "oppose", "confidence": 0.7},
                },
            }
        },
    )

    result = module.execute(context)
    assert all(
        "returned non-mapping result" not in warning
        for warning in result.outputs["council_normalization_warnings"]
    )
