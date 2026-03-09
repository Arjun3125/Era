"""Tests for council router mode routing engine/module."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from core.contracts import ExecutionContext, InputContract, ModeResolutionContract
from modules.council_router.engine import ModeRoutingEngine
from modules.council_router.mode_orchestrator import ModeOrchestrator
from modules.council_router.module import ModeRoutingModule


def test_mode_routing_engine_does_not_leak_ablation_across_runs():
    orchestrator = ModeOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    first = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context={"disable_ministers": True},
    )
    assert first.execution_plan["use_dynamic_council"] is False

    second = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context={},
    )
    assert second.execution_plan["use_dynamic_council"] is True
    assert orchestrator.config.disable_ministers is False


def test_mode_routing_engine_ignores_invalid_int_ablation_flags():
    orchestrator = ModeOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    result = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context={"disable_ministers": 2},
    )

    assert result.execution_plan["use_dynamic_council"] is True
    assert any("Invalid ablation flag 'disable_ministers' ignored." in item for item in result.warnings)


def test_mode_routing_engine_preserves_partial_minister_iterables():
    class _FaultyMinisters:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return "Chancellor"
            raise RuntimeError("boom")

    class _FaultyMinisterOrchestrator(ModeOrchestrator):
        def get_ministers_for_mode(self, mode, routing_context=None):
            _ = mode
            _ = routing_context
            return _FaultyMinisters()

    engine = ModeRoutingEngine(orchestrator=_FaultyMinisterOrchestrator())
    result = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context={},
    )

    assert result.selected_ministers == ["chancellor"]


def test_mode_routing_engine_applies_uncertainty_control_and_restores_config():
    orchestrator = ModeOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    result = engine.route(
        requested_mode="quick",
        user_input="Should I act now?",
        routing_context={
            "ablation": {"disable_kis": "1"},
            "use_uncertainty_control": "true",
            "uncertainty_signals": {
                "entropy": 0.95,
                "confidence_variance": 0.8,
                "inverse_margin": 0.9,
            },
        },
    )

    assert result.uncertainty_policy.get("applied") is True
    assert result.resolved_mode == "darbar"
    assert result.execution_plan["use_kis"] is False
    assert orchestrator.config.disable_kis is False


def test_mode_routing_module_resolves_mode_and_routing_precedence():
    module = ModeRoutingModule.create()
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Help me decide",
            metadata={
                "requested_mode": "meeting",
                "routing_context": {"domains": ["input"], "disable_pwm": False},
            },
        ),
        config={
            "requested_mode": "quick",
            "routing_context": {"domains": ["config"], "disable_pwm": False},
        },
        metadata={
            "requested_mode": "war",
            "routing_context": {"domains": ["meta"], "disable_pwm": "true"},
        },
        state={
            "requested_mode": "",  # ignored as empty
            "routing_context": {"domains": ["state"], "disable_pwm": "false"},
        },
    )

    result = module.execute(context)
    assert result.outputs["resolved_mode"] == "war"
    assert result.outputs["execution_plan"]["use_pwm"] is True

    sources = result.outputs["mode_routing_sources"]
    assert "context.config.routing_context" in sources
    assert "input.metadata.routing_context" in sources
    assert "run.metadata.routing_context" in sources
    assert "state.routing_context" in sources


def test_mode_routing_module_degrades_when_engine_raises():
    class _ExplodingEngine:
        def route(self, **kwargs):
            raise RuntimeError("routing exploded")

    module = ModeRoutingModule(
        orchestrator=ModeOrchestrator(),
        engine=_ExplodingEngine(),  # type: ignore[arg-type]
    )
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"requested_mode": "war"},
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    assert result.outputs["resolved_mode"] == "war"
    assert result.outputs["mode_routing_metadata"]["mode_resolution_reason"] == "engine_exception"
    assert any("RuntimeError" in item for item in result.errors)


def test_mode_routing_module_fallback_execution_plan_normalizes_keys_and_values():
    class _PlanOrchestrator(ModeOrchestrator):
        def get_execution_plan(self, mode):
            _ = mode
            return [
                (b"use-dynamic-council", "1"),
                ("use_ml_prior", "0"),
                ("use_kis", True),
                ("use_pwm", "false"),
                ("use_memory", "1"),
            ]

    class _ExplodingEngine:
        def route(self, **kwargs):
            raise RuntimeError("routing exploded")

    module = ModeRoutingModule(
        orchestrator=_PlanOrchestrator(),
        engine=_ExplodingEngine(),  # type: ignore[arg-type]
    )
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        state={"requested_mode": "war"},
    )

    result = module.execute(context)
    assert result.status.value == "degraded"
    assert result.outputs["execution_plan"] == {
        "use_dynamic_council": True,
        "use_ml_prior": False,
        "use_kis": True,
        "use_pwm": False,
        "use_memory": True,
    }


def test_mode_routing_engine_normalizes_invalid_routing_context_payload():
    orchestrator = ModeOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    result = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context="not-a-mapping",  # type: ignore[arg-type]
    )

    assert result.resolved_mode == "meeting"
    assert result.execution_plan["use_dynamic_council"] is True
    assert any("Invalid routing_context payload" in warning for warning in result.warnings)


def test_mode_routing_engine_accepts_json_routing_context_payload():
    orchestrator = ModeOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    result = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context='{"disable_pwm":"true"}',  # type: ignore[arg-type]
    )

    assert result.execution_plan["use_pwm"] is False


def test_mode_routing_engine_accepts_iterable_routing_context_payload():
    orchestrator = ModeOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    result = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context=[
            ("disable_pwm", "true"),
            ("uncertainty_signals", [("entropy", 0.95), ("inverse_margin", 0.9)]),
            ("use_uncertainty_control", "1"),
        ],  # type: ignore[arg-type]
    )

    assert result.execution_plan["use_pwm"] is False
    assert all(
        "routing_context.uncertainty_signals" not in warning
        for warning in result.warnings
    )


def test_mode_routing_engine_handles_invalid_uncertainty_policy_payload():
    class _BadPolicyOrchestrator(ModeOrchestrator):
        def apply_uncertainty_control(self, *, signals, base_mode="meeting"):
            return "bad-policy"

    orchestrator = _BadPolicyOrchestrator()
    engine = ModeRoutingEngine(orchestrator=orchestrator)

    result = engine.route(
        requested_mode="meeting",
        user_input="Need guidance",
        routing_context={
            "use_uncertainty_control": True,
            "uncertainty_signals": {"entropy": 0.9},
        },
    )

    assert result.resolved_mode == "meeting"
    assert result.uncertainty_policy["applied"] is False
    assert any("Invalid uncertainty policy payload" in warning for warning in result.warnings)


def test_mode_routing_module_reads_normalized_requested_mode_and_routing_keys():
    module = ModeRoutingModule.create()
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Help me decide",
            metadata={
                "requested-mode": "war",
                "routing-context": {"disable-pwm": "true"},
            },
        ),
    )

    result = module.execute(context)
    assert result.outputs["resolved_mode"] == "war"
    assert result.outputs["execution_plan"]["use_pwm"] is False
    assert "input.metadata.routing_context" in result.outputs["mode_routing_sources"]


def test_mode_routing_module_accepts_iterable_routing_context_sources():
    module = ModeRoutingModule.create()
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Help me decide",
            metadata={"routing_context": [(b"disable_pwm", "true")]},  # type: ignore[arg-type]
        ),
    )

    result = module.execute(context)
    assert result.outputs["execution_plan"]["use_pwm"] is False
    assert "input.metadata.routing_context" in result.outputs["mode_routing_sources"]


def test_mode_routing_module_preserves_partial_iterable_engine_payload():
    class _PartialMinisters:
        def __iter__(self):
            yield "Risk"
            raise RuntimeError("ministers-iter-failed")

    class _PartialWarnings:
        def __iter__(self):
            yield "warn-a"
            yield "warn-b"
            raise RuntimeError("warnings-iter-failed")

    class _PartialMapping(Mapping):
        def __init__(self, items):
            self._items = list(items)

        def __getitem__(self, key):
            for raw_key, value in self._items:
                if raw_key == key:
                    return value
            raise KeyError(key)

        def __iter__(self):
            for raw_key, _ in self._items:
                yield raw_key
            raise RuntimeError("mapping-iter-failed")

        def __len__(self):
            return len(self._items)

        def items(self):
            for item in self._items:
                yield item
            raise RuntimeError("mapping-items-failed")

    @dataclass
    class _RouteResult:
        resolved_mode: str = "war"
        should_invoke_council: bool = True
        selected_ministers: object = field(default_factory=_PartialMinisters)
        frame: str = "frame"
        execution_plan: object = field(
            default_factory=lambda: _PartialMapping([("use_dynamic_council", True), ("use_kis", False)])
        )
        mode_contract: ModeResolutionContract = field(
            default_factory=lambda: ModeResolutionContract(
                mode="war",
                should_invoke_council=True,
                selected_ministers=["risk"],
                rationale="stub",
                confidence=0.9,
            )
        )
        warnings: object = field(default_factory=_PartialWarnings)
        uncertainty_policy: object = field(
            default_factory=lambda: _PartialMapping([("applied", True), ("u", 0.8)])
        )
        routing_metadata: object = field(
            default_factory=lambda: _PartialMapping(
                [("requested_mode_raw", "war"), ("mode_resolution_reason", "stub")]
            )
        )

    class _PartialEngine:
        def route(self, **kwargs):
            _ = kwargs
            return _RouteResult()

    module = ModeRoutingModule(
        orchestrator=ModeOrchestrator(),
        engine=_PartialEngine(),  # type: ignore[arg-type]
    )
    context = ExecutionContext(
        input_contract=InputContract(user_input="Help me decide"),
        state={"requested_mode": "war"},
    )

    result = module.execute(context)

    assert result.outputs["selected_ministers"] == ["risk"]
    assert result.outputs["execution_plan"]["use_dynamic_council"] is True
    assert result.outputs["execution_plan"]["use_kis"] is False
    assert result.outputs["mode_routing_warnings"] == ["warn-a", "warn-b"]
    assert result.outputs["mode_uncertainty_policy"]["applied"] is True


def test_mode_orchestrator_uncertainty_control_handles_invalid_margin_and_base_mode():
    orchestrator = ModeOrchestrator()
    policy = orchestrator.apply_uncertainty_control(
        signals={"decision_margin": "invalid", "entropy": 0.9},
        base_mode="unknown_mode",
    )

    assert policy["target_mode"] in {"meeting", "darbar"}
    assert 0.0 <= policy["u"] <= 1.0
