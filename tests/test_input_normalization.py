"""Tests for input normalization engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from core.contracts import ExecutionContext, InputContract, RequestContextContract
from modules.input_normalization.engine import InputNormalizationEngine
from modules.input_normalization.module import InputNormalizationModule


class _CustomValue:
    def __str__(self) -> str:
        return "custom_value"


class _FaultyRoutingContext(Mapping):
    def __getitem__(self, key):
        data = {
            "domain": _FaultyDomains(),
            "key_entities": _FaultyEntities(),
        }
        return data[key]

    def __iter__(self):
        yield "domain"
        yield "key_entities"
        raise RuntimeError("routing-context-iter-failed")

    def __len__(self) -> int:
        return 2

    def items(self):
        yield ("domain", _FaultyDomains())
        yield ("key_entities", _FaultyEntities())
        raise RuntimeError("routing-context-items-failed")


class _FaultyDomains:
    def __iter__(self):
        yield "Strategy"
        raise RuntimeError("domains-iter-failed")


class _FaultyEntities:
    def __iter__(self):
        yield "Alice"
        raise RuntimeError("entities-iter-failed")


def test_input_normalization_engine_clamps_and_sanitizes():
    engine = InputNormalizationEngine()
    result = engine.normalize(
        requested_mode="quick_mode",
        routing_context={
            "domains": ["Strategy", "strategy", "Ops"],
            "domain_confidence": "nan",
            "stakes": "critical",
            "reversibility": True,
            "domain_scores": {
                "strategy": "inf",
                "ops": 0.6,
            },
            "path_hint": Path("data/logs"),
            "opaque": _CustomValue(),
            "drop_me": float("nan"),
        },
    )

    assert result.normalized_mode == "quick"
    assert result.contract.requested_mode == "quick"

    context = result.normalized_routing_context
    assert context["domains"] == ["strategy", "ops"]
    assert context["domain_confidence"] == 0.0
    assert context["stakes"] == "high"
    assert context["reversibility"] == "fully_reversible"
    assert context["domain_scores"] == {"ops": 0.6}
    assert context["path_hint"] == str(Path("data/logs"))
    assert context["opaque"] == "custom_value"
    assert "drop_me" not in context

    warnings_blob = "\n".join(result.warnings)
    assert "Non-finite domain_confidence normalized to 0.0." in warnings_blob
    assert "Non-finite domain_scores value for 'strategy' ignored." in warnings_blob
    assert "routing_context.opaque used non-serializable value and was stringified." in warnings_blob


def test_input_normalization_engine_accepts_bytes_payloads_and_iterables():
    engine = InputNormalizationEngine(default_mode="meeting")
    result = engine.normalize(
        requested_mode=b"crisis",
        routing_context=b'{"domain": ["AI", "ai"], "reversible": "no", "key_entities": ["x", 1], "domain_scores": {"ai": "1.2", "ops": -0.5}}',
    )

    assert result.normalized_mode == "war"
    assert result.normalized_routing_context["domains"] == ["ai"]
    assert result.normalized_routing_context["reversibility"] == "irreversible"
    assert result.normalized_routing_context["key_entities"] == ["x", "1"]
    assert result.normalized_routing_context["domain_scores"] == {"ai": 1.0, "ops": 0.0}


def test_input_normalization_engine_accepts_iterable_routing_context_mapping():
    engine = InputNormalizationEngine(default_mode="meeting")
    result = engine.normalize(
        requested_mode="standard",
        routing_context=[
            ("domain", ["AI", "ai"]),
            ("reversible", "yes"),
            ("domain_scores", [("ai", "1.3"), ("ops", -0.2)]),
        ],
    )

    assert result.normalized_mode == "meeting"
    assert result.normalized_routing_context["domains"] == ["ai"]
    assert result.normalized_routing_context["reversibility"] == "fully_reversible"
    assert result.normalized_routing_context["domain_scores"] == {"ai": 1.0, "ops": 0.0}


def test_input_normalization_engine_flags_invalid_falsey_iterable_routing_context():
    engine = InputNormalizationEngine(default_mode="meeting")
    result = engine.normalize(
        requested_mode="meeting",
        routing_context=[{"a": 1, "b": 2}],  # type: ignore[arg-type]
    )

    assert result.normalized_routing_context == {}
    warnings_blob = "\n".join(result.warnings)
    assert "Invalid routing_context payload ignored during normalization." in warnings_blob


def test_input_normalization_engine_preserves_partial_iterable_values():
    engine = InputNormalizationEngine(default_mode="meeting")
    result = engine.normalize(
        requested_mode="meeting",
        routing_context=_FaultyRoutingContext(),  # type: ignore[arg-type]
    )

    assert result.normalized_routing_context["domains"] == ["strategy"]
    assert result.normalized_routing_context["key_entities"] == ["Alice"]
    assert any("partial" in warning.lower() for warning in result.warnings)


def test_input_normalization_module_merges_sources_with_explicit_precedence():
    module = InputNormalizationModule.create()

    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Test",
            metadata={
                "requested_mode": "meeting",
                "routing_context": {
                    "domains": ["input"],
                    "stakes": "medium",
                },
            },
        ),
        config={
            "requested_mode": "quick",
            "routing_context": {
                "domains": ["config"],
                "stakes": "low",
            },
        },
        metadata={
            "requested_mode": "war",
            "routing_context": {
                "domains": ["runtime"],
                "reversibility": "reversible",
            },
        },
        state={
            "routing_context": {
                "domains": ["state"],
                "domain_confidence": 1.2,
            },
        },
    )

    output = module.execute(context)
    routing_context = output.outputs["routing_context"]

    assert output.outputs["requested_mode"] == "war"
    assert routing_context["domains"] == ["state"]
    assert routing_context["stakes"] == "medium"
    assert routing_context["reversibility"] == "fully_reversible"
    assert routing_context["domain_confidence"] == 1.0

    sources = output.outputs["request_context_sources"]
    assert "context.config.routing_context" in sources
    assert "input.metadata.routing_context" in sources
    assert "run.metadata.routing_context" in sources
    assert "state.routing_context" in sources


def test_input_normalization_module_accepts_iterable_routing_context_sources():
    module = InputNormalizationModule.create()

    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Test",
            metadata={
                "routing_context": [("domain", ["input"]), ("stakes", "critical")],
            },
        ),
    )

    output = module.execute(context)
    assert output.outputs["routing_context"]["domains"] == ["input"]
    assert output.outputs["routing_context"]["stakes"] == "high"
    assert "input.metadata.routing_context" in output.outputs["request_context_sources"]


def test_input_normalization_module_uses_routing_mode_when_explicit_mode_missing():
    module = InputNormalizationModule.create()

    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Test",
            metadata={
                "routing_context": {
                    "mode": "crisis",
                }
            },
        ),
    )

    output = module.execute(context)
    assert output.outputs["requested_mode"] == "war"


class _MalformedInputNormalizationEngine:
    default_mode = "meeting"

    def normalize(self, **kwargs):
        return {
            "normalized_mode": "",
            "normalized_routing_context": "bad-routing",
            "contract": "bad-contract",
            "warnings": "legacy-warning",
        }


class _ExplodingInputNormalizationEngine:
    default_mode = "meeting"

    def normalize(self, **kwargs):
        raise RuntimeError("normalize boom")


class _PartialIterable:
    def __init__(self, *items):
        self._items = items

    def __iter__(self):
        for item in self._items:
            yield item
        raise RuntimeError("iter-failed")


class _PartialPayloadMapping(dict):
    def items(self):
        def _items():
            yield ("normalized-mode", "crisis")
            yield ("normalized-routing-context", [("domain", ["ops"])])
            yield ("warnings", _PartialIterable("warn_a", "warn_b"))
            raise RuntimeError("items-failed")

        return _items()


def test_input_normalization_module_normalizes_malformed_engine_payload():
    module = InputNormalizationModule(engine=_MalformedInputNormalizationEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="x", metadata={"requested_mode": "war"}),
    )

    output = module.execute(context)
    assert output.status.value == "degraded"
    assert output.outputs["requested_mode"] == "war"
    assert output.outputs["routing_context"] == {}
    assert isinstance(output.outputs["request_context_contract"], RequestContextContract)
    assert "legacy-warning" in output.outputs["request_context_warnings"]


def test_input_normalization_module_degrades_on_engine_exception():
    module = InputNormalizationModule(engine=_ExplodingInputNormalizationEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))

    output = module.execute(context)
    assert output.status.value == "degraded"
    assert output.outputs["request_context_contract"].source == "input_normalization.module.exception"
    assert output.outputs["routing_context"] == {}
    assert any("RuntimeError" in err for err in output.errors)


def test_input_normalization_module_handles_normalized_keys_and_iterable_warnings():
    class _VariantInputNormalizationEngine:
        default_mode = "meeting"

        def normalize(self, **kwargs):
            return {
                "normalized-mode": 0,
                "normalized-routing-context": {1: "x"},
                "contract": "bad-contract",
                "warnings": (item for item in [b" warn ", "warn", ""]),
            }

    module = InputNormalizationModule(engine=_VariantInputNormalizationEngine())
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="x",
            metadata={
                "requested-mode": "crisis",
                "routing-context": {"risk-level": "critical"},
            },
        ),
    )

    output = module.execute(context)
    assert output.status.value == "degraded"
    assert output.outputs["requested_mode"] == "0"
    assert output.outputs["routing_context"]["1"] == "x"
    assert "warn" in output.outputs["request_context_warnings"]


def test_input_normalization_module_accepts_iterable_engine_payload():
    class _IterablePayloadInputNormalizationEngine:
        default_mode = "meeting"

        def normalize(self, **kwargs):
            return [
                ("normalized-mode", "crisis"),
                ("normalized-routing-context", [("domain", ["ops"]), ("stakes", "critical")]),
                (
                    "contract",
                    [
                        ("mode", "quick"),
                        ("routing_context", [("domain", ["finance"])]),
                        ("source", "legacy"),
                    ],
                ),
                ("warnings", [b" warn ", "warn"]),
            ]

    module = InputNormalizationModule(engine=_IterablePayloadInputNormalizationEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))

    output = module.execute(context)
    contract = output.outputs["request_context_contract"]
    assert output.outputs["requested_mode"] == "crisis"
    assert output.outputs["routing_context"]["domain"] == ["ops"]
    assert contract.requested_mode == "quick"
    assert contract.routing_context == {"domain": ["finance"]}
    assert contract.source == "legacy"
    assert "warn" in output.outputs["request_context_warnings"]


def test_input_normalization_module_preserves_partial_engine_payload_items():
    class _PartialPayloadInputNormalizationEngine:
        default_mode = "meeting"

        def normalize(self, **kwargs):
            return _PartialPayloadMapping()

    module = InputNormalizationModule(engine=_PartialPayloadInputNormalizationEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="x"))

    output = module.execute(context)

    assert output.outputs["requested_mode"] == "crisis"
    assert output.outputs["routing_context"]["domain"] == ["ops"]
    assert output.outputs["request_context_warnings"] == ["warn_a", "warn_b"]
