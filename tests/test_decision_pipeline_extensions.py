"""Tests for decision pipeline extension stage planning."""

from __future__ import annotations

import pytest

from core.contracts import ExecutionContext
from modules.decision_pipeline.extensions import ExtensionStagePlanner, ExtensionStageSpec


def _handler(_context: ExecutionContext):
    return {}


def _base_plan() -> list[ExtensionStageSpec]:
    return [
        ExtensionStageSpec(name="input", handler=_handler, source="core"),
        ExtensionStageSpec(name="routing", handler=_handler, source="core"),
    ]


class _PartialFailingSpecIterable:
    def __iter__(self):
        yield ExtensionStageSpec(name="ext_a", handler=_handler, after="routing")
        yield ExtensionStageSpec(name="ext_b", handler=_handler, after="ext_a")
        raise RuntimeError("iterator boom")


def test_extension_planner_preserves_declaration_order_for_same_after_anchor():
    planner = ExtensionStagePlanner()
    plan = planner.compose(
        base_plan=_base_plan(),
        extensions=[
            ExtensionStageSpec(name="ext_a", handler=_handler, after="routing"),
            ExtensionStageSpec(name="ext_b", handler=_handler, after="routing"),
            ExtensionStageSpec(name="ext_c", handler=_handler, after="routing"),
        ],
    )
    assert [item.name for item in plan] == ["input", "routing", "ext_a", "ext_b", "ext_c"]


def test_extension_planner_resolves_anchor_chain_against_extension_names():
    planner = ExtensionStagePlanner()
    plan = planner.compose(
        base_plan=_base_plan(),
        extensions=[
            ExtensionStageSpec(name="ext_x", handler=_handler, after="routing"),
            ExtensionStageSpec(name="ext_y", handler=_handler, after="ext_x"),
            ExtensionStageSpec(name="ext_z", handler=_handler, before="ext_y"),
        ],
    )
    assert [item.name for item in plan] == ["input", "routing", "ext_x", "ext_z", "ext_y"]


def test_extension_planner_rejects_unknown_anchor_early():
    planner = ExtensionStagePlanner()
    with pytest.raises(ValueError, match="unknown stage"):
        planner.compose(
            base_plan=_base_plan(),
            extensions=[
                ExtensionStageSpec(name="ext_bad", handler=_handler, after="missing_stage"),
            ],
        )


def test_extension_planner_normalizes_on_error_policy_case():
    planner = ExtensionStagePlanner()
    plan = planner.compose(
        base_plan=_base_plan(),
        extensions=[
            ExtensionStageSpec(name="ext_case", handler=_handler, after="routing", on_error="DEGRADE"),
        ],
    )
    extension = [item for item in plan if item.name == "ext_case"][0]
    assert extension.on_error == "degrade"


def test_extension_planner_rejects_cyclic_dependency():
    planner = ExtensionStagePlanner()
    with pytest.raises(ValueError, match="Unresolvable extension anchors"):
        planner.compose(
            base_plan=_base_plan(),
            extensions=[
                ExtensionStageSpec(name="ext_a", handler=_handler, after="ext_b"),
                ExtensionStageSpec(name="ext_b", handler=_handler, after="ext_a"),
            ],
        )


def test_extension_planner_rejects_non_sequence_inputs():
    planner = ExtensionStagePlanner()
    with pytest.raises(TypeError, match="base_plan must be a sequence"):
        planner.compose(base_plan="bad", extensions=[])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="extensions must be a sequence"):
        planner.compose(base_plan=_base_plan(), extensions="bad")  # type: ignore[arg-type]


def test_extension_planner_rejects_invalid_base_stage_handler_and_policy():
    planner = ExtensionStagePlanner()
    with pytest.raises(TypeError, match="Base stage 'input' handler must be callable"):
        planner.compose(
            base_plan=[
                ExtensionStageSpec(name="input", handler=None),  # type: ignore[arg-type]
                ExtensionStageSpec(name="routing", handler=_handler),
            ],
            extensions=[],
        )

    with pytest.raises(ValueError, match="Base stage 'input' on_error must be one of"):
        planner.compose(
            base_plan=[
                ExtensionStageSpec(name="input", handler=_handler, on_error="warn"),
                ExtensionStageSpec(name="routing", handler=_handler),
            ],
            extensions=[],
        )


def test_extension_planner_accepts_iterable_inputs_and_decodes_bytes_fields():
    planner = ExtensionStagePlanner()
    base_plan = iter(_base_plan())
    extensions = (
        spec
        for spec in [
            ExtensionStageSpec(
                name=b" ext_bytes ",
                handler=_handler,
                after=b"routing",
                on_error=b"DEGRADE",
                source=b" custom ",
            )
        ]
    )

    plan = planner.compose(base_plan=base_plan, extensions=extensions)
    names = [item.name for item in plan]
    assert names == ["input", "routing", "ext_bytes"]
    extension = plan[-1]
    assert extension.on_error == "degrade"
    assert extension.source == "custom"


def test_extension_planner_preserves_partial_iterable_extensions():
    planner = ExtensionStagePlanner()
    plan = planner.compose(
        base_plan=_base_plan(),
        extensions=_PartialFailingSpecIterable(),  # type: ignore[arg-type]
    )

    assert [item.name for item in plan] == ["input", "routing", "ext_a", "ext_b"]
