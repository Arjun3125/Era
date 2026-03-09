"""Tests for council execution engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from core.contracts import ExecutionContext, InputContract
from modules.council_execution.engine import CouncilExecutionEngine
from modules.council_execution.module import CouncilExecutionModule


class _Minister:
    def __init__(self, stance: str = "support", confidence: float = 0.8, red_line: bool = False):
        self._stance = stance
        self._confidence = confidence
        self._red_line = red_line

    def analyze(self, user_input: str, context):
        return {
            "stance": self._stance,
            "confidence": self._confidence,
            "reasoning": f"analysis for {user_input}",
            "red_line_triggered": self._red_line,
        }


class _StubCouncil:
    def __init__(self):
        self.ministers = {
            "grand_strategist": _Minister("support", 0.9),
            "risk": _Minister("oppose", 0.4),
        }


class _FaultyMinistersMapping(Mapping):
    def __getitem__(self, key):
        if key == "grand_strategist":
            return _Minister("support", 0.95)
        raise KeyError(key)

    def __iter__(self):
        yield "grand_strategist"
        raise RuntimeError("ministers-iter-failed")

    def __len__(self):
        return 1

    def items(self):
        yield ("grand_strategist", _Minister("support", 0.95))
        raise RuntimeError("ministers-items-failed")


class _FaultySelectedMinisters:
    def __iter__(self):
        yield "grand_strategy"
        raise RuntimeError("selected-ministers-iter-failed")


def test_council_execution_mode_alias_quick_skips_council():
    engine = CouncilExecutionEngine.create(council_factory=lambda llm: _StubCouncil())

    result = engine.convene(
        mode="quick_mode",
        user_input="Need quick guidance",
        context={},
    )

    assert result["mode"] == "quick"
    assert result["outcome"] == "quick_mode_direct_response"
    warnings_blob = "\n".join(result.get("warnings", []))
    assert "Mode alias 'quick_mode' normalized to 'quick'." in warnings_blob


def test_council_execution_selected_minister_aliases_and_unknowns():
    engine = CouncilExecutionEngine.create(council_factory=lambda llm: _StubCouncil())

    result = engine.convene(
        mode="meeting",
        user_input="Plan strategic move",
        context={},
        selected_ministers=["grand_strategy", "unknown_minister"],
    )

    assert result["ministers_involved"] == ["grand_strategist"]
    assert result["recommendation"] == "strong_consensus_support"
    warnings_blob = "\n".join(result.get("warnings", []))
    assert "minister alias 'grand_strategy' normalized to 'grand_strategist'." in warnings_blob
    assert "unknown minister 'unknown_minister' ignored." in warnings_blob


def test_council_execution_selected_ministers_support_iterables_and_int_redline_is_ignored():
    class _IntRedLineCouncil(_StubCouncil):
        def __init__(self):
            self.ministers = {"grand_strategist": _Minister("support", 0.9, red_line=2)}

    engine = CouncilExecutionEngine.create(council_factory=lambda llm: _IntRedLineCouncil())
    result = engine.convene(
        mode="meeting",
        user_input="Plan strategic move",
        context={},
        selected_ministers=(item for item in [b"grand_strategy"]),
    )

    assert result["ministers_involved"] == ["grand_strategist"]
    assert result["red_line_concerns"] == []


def test_council_execution_preserves_partial_minister_registry_and_selection_iterables():
    class _FaultyCouncil:
        def __init__(self):
            self.ministers = _FaultyMinistersMapping()

    engine = CouncilExecutionEngine.create(council_factory=lambda llm: _FaultyCouncil())
    result = engine.convene(
        mode="meeting",
        user_input="Need guidance",
        context={},
        selected_ministers=_FaultySelectedMinisters(),  # type: ignore[arg-type]
    )

    assert result["ministers_involved"] == ["grand_strategist"]
    assert any("partial" in warning.lower() for warning in result.get("warnings", []))


@dataclass
class _ExplodingEngine:
    disabled: bool = False

    def get_current_mode(self) -> str:
        return "meeting"

    def convene(self, **kwargs):
        raise RuntimeError("boom")


def test_council_execution_module_degrades_on_engine_exception():
    module = CouncilExecutionModule(engine=_ExplodingEngine())

    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Need council output",
            metadata={"routing_context": {"domains": ["input"]}},
        ),
        config={"routing_context": {"domains": ["config"]}},
        metadata={"routing_context": {"domains": ["runtime"]}},
        state={"routing_context": {"domains": ["state"]}},
    )

    result = module.execute(context)

    assert result.status.value == "degraded"
    assert result.outputs["council_result"]["outcome"] == "engine_error"
    assert result.outputs["council_contract"].consensus_strength == 0.0
    sources = result.outputs["council_execution_sources"]
    assert "context.config.routing_context" in sources
    assert "input.metadata.routing_context" in sources
    assert "run.metadata.routing_context" in sources
    assert "state.routing_context" in sources


@dataclass
class _MalformedPayloadEngine:
    disabled: bool = False

    def get_current_mode(self) -> str:
        return "meeting"

    def convene(self, **kwargs):
        return ["not-a-mapping"]


def test_council_execution_module_normalizes_malformed_engine_payload():
    module = CouncilExecutionModule(engine=_MalformedPayloadEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="Need council output"))

    result = module.execute(context)

    assert result.status.value == "degraded"
    assert result.outputs["council_result"]["outcome"] == "not_invoked"
    assert result.outputs["council_result"]["recommendation"] == "defer"
    assert result.outputs["council_result"]["mode"] == "meeting"
    assert result.outputs["council_result"]["warning_count"] >= 1
    assert any(
        "non-mapping result" in warning
        for warning in result.outputs["council_warnings"]
    )


def test_council_execution_module_reads_normalized_context_and_result_keys():
    class _CapturingEngine:
        disabled = False

        def __init__(self):
            self.last_kwargs = {}

        def get_current_mode(self) -> str:
            return "meeting"

        def convene(self, **kwargs):
            self.last_kwargs = kwargs
            return {
                "outcome": "standard_consensus",
                "recommendation": "proceed",
                "mode": "war",
                "minister-outputs": {"grand_strategist": {"stance": "support", "confidence": 0.7}},
                "warnings": [b"warn"],
            }

    engine = _CapturingEngine()
    module = CouncilExecutionModule(engine=engine)  # type: ignore[arg-type]
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Need council output",
            metadata={"requested-mode": "war", "routing-context": {"domains": ["input"]}},
        ),
        state={"selected-ministers": ["grand_strategy"]},
    )

    result = module.execute(context)
    assert engine.last_kwargs["mode"] == "war"
    assert engine.last_kwargs["selected_ministers"] == ["grand_strategy"]
    assert result.outputs["council_result"]["minister_positions"]["grand_strategist"]["stance"] == "support"
    assert "warn" in result.outputs["council_warnings"]


def test_council_execution_module_accepts_iterable_routing_context_and_engine_payload():
    class _IterableEngine:
        disabled = False

        def __init__(self):
            self.last_kwargs = {}

        def get_current_mode(self) -> str:
            return "meeting"

        def convene(self, **kwargs):
            self.last_kwargs = kwargs
            return [
                ("outcome", "standard_consensus"),
                ("recommendation", "proceed"),
                ("mode", "war"),
                (
                    "minister_outputs",
                    [("grand_strategist", [("stance", "support"), ("confidence", "0.7")])],
                ),
                ("warnings", ["iter-warn"]),
            ]

    engine = _IterableEngine()
    module = CouncilExecutionModule(engine=engine)  # type: ignore[arg-type]
    context = ExecutionContext(
        input_contract=InputContract(user_input="Need council output"),
        state={
            "routing_context": [
                ("requested_mode", "war"),
                ("selected_ministers", ["grand_strategy"]),
                ("domains", ["strategy"]),
            ]
        },  # type: ignore[arg-type]
    )

    result = module.execute(context)
    assert engine.last_kwargs["mode"] == "war"
    assert engine.last_kwargs["selected_ministers"] == ["grand_strategy"]
    assert result.outputs["council_result"]["minister_positions"]["grand_strategist"]["confidence"] == 0.7
    assert result.outputs["council_warnings"] == ["iter-warn"]


def test_council_execution_module_preserves_partial_iterable_engine_payload():
    class _PartialWarnings:
        def __iter__(self):
            yield "warn-a"
            yield "warn-b"
            raise RuntimeError("warn-iter-failed")

    class _PartialPayload(Mapping):
        def __getitem__(self, key):
            data = {
                "outcome": "standard_consensus",
                "recommendation": "proceed",
                "minister_outputs": [("grand_strategist", [("stance", "support"), ("confidence", "0.7")])],
                "warnings": _PartialWarnings(),
            }
            return data[key]

        def __iter__(self):
            yield "outcome"
            yield "recommendation"
            yield "minister_outputs"
            yield "warnings"
            raise RuntimeError("payload-iter-failed")

        def __len__(self):
            return 4

        def items(self):
            yield ("outcome", "standard_consensus")
            yield ("recommendation", "proceed")
            yield ("minister_outputs", [("grand_strategist", [("stance", "support"), ("confidence", "0.7")])])
            yield ("warnings", _PartialWarnings())
            raise RuntimeError("payload-items-failed")

    class _PartialEngine:
        disabled = False

        def get_current_mode(self) -> str:
            return "meeting"

        def convene(self, **kwargs):
            return _PartialPayload()

    module = CouncilExecutionModule(engine=_PartialEngine())  # type: ignore[arg-type]
    context = ExecutionContext(input_contract=InputContract(user_input="Need council output"))

    result = module.execute(context)
    assert result.outputs["council_result"]["minister_positions"]["grand_strategist"]["confidence"] == 0.7
    assert result.outputs["council_warnings"] == ["warn-a", "warn-b"]
