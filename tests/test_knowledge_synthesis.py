"""Tests for knowledge synthesis engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import modules.knowledge_synthesis.engine as ks_engine
from core.contracts import ExecutionContext, InputContract, KnowledgeContract
from modules.knowledge_synthesis.engine import KnowledgeSynthesisEngine
from modules.knowledge_synthesis.module import KnowledgeSynthesisModule


def test_knowledge_engine_resolve_inputs_normalizes_mode_and_context():
    engine = KnowledgeSynthesisEngine()

    inputs = engine.resolve_inputs(
        mode="quick_mode",
        routing_context={
            "domains": "Strategy, strategy, Risk",
            "confidence": "nan",
            "kis_max_items": "999",
            "synthesized_knowledge": ["existing ctx", "existing ctx"],
        },
    )

    assert inputs.active_domains == ["strategy", "risk"]
    assert inputs.domain_confidence == engine.default_domain_confidence
    assert inputs.max_items == engine.max_items_upper_bound
    assert inputs.extra_context == ["existing ctx"]

    warnings = "\n".join(inputs.warnings)
    assert "Non-finite domain_confidence normalized to default value." in warnings
    assert "kis_max_items above" in warnings


def test_knowledge_engine_resolve_inputs_accepts_bytes_and_iterables():
    engine = KnowledgeSynthesisEngine()
    inputs = engine.resolve_inputs(
        mode=b"quick_mode",
        routing_context={
            b"active_domains": (item for item in ["Strategy", "strategy"]),
            b"domain_confidence": b"1.5",
            b"extra_context": (item for item in [b"a", "a", {"k": 1}]),
        },
    )

    assert inputs.active_domains == ["strategy"]
    assert inputs.domain_confidence == 1.0
    assert inputs.max_items == 5
    assert inputs.extra_context == ["a", '{"k": 1}']


def test_knowledge_engine_resolve_inputs_accepts_iterable_routing_context_mapping():
    engine = KnowledgeSynthesisEngine()
    inputs = engine.resolve_inputs(
        mode="meeting",
        routing_context=[
            ("domains", ["strategy", "risk"]),
            ("domain_confidence", "0.6"),
            ("max_items", "7"),
        ],  # type: ignore[arg-type]
    )

    assert inputs.active_domains == ["strategy", "risk"]
    assert inputs.domain_confidence == 0.6
    assert inputs.max_items == 7


def test_knowledge_engine_resolve_inputs_preserves_partial_domain_iterables():
    class _FaultyDomains:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return "Strategy"
            raise RuntimeError("boom")

    engine = KnowledgeSynthesisEngine()
    inputs = engine.resolve_inputs(
        mode="meeting",
        routing_context={"domains": _FaultyDomains()},
    )

    assert inputs.active_domains == ["strategy"]
    assert any("Invalid domains payload" in item for item in inputs.warnings)


def test_knowledge_engine_run_sanitizes_result_payload(monkeypatch):
    engine = KnowledgeSynthesisEngine()

    def _fake_synthesize_knowledge(**kwargs):
        return {
            "synthesized_knowledge": "single item",
            "knowledge_trace": {
                "source": Path("logs/trace.json"),
                "timestamp": datetime(2026, 3, 4, tzinfo=timezone.utc),
            },
            "knowledge_quality": {
                "candidate_quality": "nan",
                "top_kis": ["0.8", "bad", float("inf")],
                "avg_kis": "1.25",
            },
            "knowledge_debug": {
                "raw": {"path": Path("logs/debug.json")},
            },
        }

    monkeypatch.setattr(ks_engine, "synthesize_knowledge", _fake_synthesize_knowledge)

    result = engine.run(
        user_input="Help with career transition",
        active_domains=["career"],
        domain_confidence=0.8,
        max_items=3,
        extra_context=["context line"],
    )

    payload = result.knowledge_result
    assert payload["synthesized_knowledge"] == ["single item"]
    assert isinstance(payload["knowledge_trace"], list)
    assert payload["knowledge_trace"][0]["source"] == str(Path("logs/trace.json"))
    assert payload["knowledge_quality"]["candidate_quality"] == 0.0
    assert payload["knowledge_quality"]["top_kis"] == [0.8]


def test_knowledge_engine_run_preserves_partial_iterable_result_fields(monkeypatch):
    class _FaultySynthesized:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return "item-1"
            raise RuntimeError("boom")

    class _FaultyTrace:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return {"source": "s1"}
            raise RuntimeError("boom")

    def _fake_synthesize_knowledge(**kwargs):
        return {
            "synthesized_knowledge": _FaultySynthesized(),
            "knowledge_trace": _FaultyTrace(),
            "knowledge_quality": {"candidate_quality": 0.5},
        }

    monkeypatch.setattr(ks_engine, "synthesize_knowledge", _fake_synthesize_knowledge)
    result = KnowledgeSynthesisEngine().run(
        user_input="Need strategic advice",
        active_domains=["strategy"],
        domain_confidence=0.7,
        max_items=3,
        extra_context=[],
    )

    assert result.knowledge_result["synthesized_knowledge"] == ["item-1"]
    assert result.knowledge_result["knowledge_trace"] == [{"source": "s1"}]
    assert any("synthesized_knowledge normalized to list" in item for item in result.warnings)
    assert any("knowledge_trace normalized to list" in item for item in result.warnings)


def test_knowledge_engine_run_accepts_bytes_result_payload(monkeypatch):
    engine = KnowledgeSynthesisEngine()

    def _fake_synthesize_knowledge(**kwargs):
        return b'{"synthesized_knowledge": ["item"], "knowledge_quality": {"candidate_quality": "0.6"}}'

    monkeypatch.setattr(ks_engine, "synthesize_knowledge", _fake_synthesize_knowledge)
    result = engine.run(
        user_input="Need strategic advice",
        active_domains=["strategy"],
        domain_confidence=0.7,
        max_items=3,
        extra_context=[],
    )

    assert result.knowledge_result["synthesized_knowledge"] == ["item"]
    assert result.knowledge_result["knowledge_quality"]["candidate_quality"] == 0.6


def test_knowledge_module_merges_routing_sources_and_emits_contract(monkeypatch):
    module = KnowledgeSynthesisModule.create()

    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Need strategic advice",
            metadata={
                "requested_mode": "meeting",
                "routing_context": {"domains": ["input"], "max_items": 2},
            },
        ),
        config={
            "requested_mode": "quick",
            "routing_context": {"domains": ["config"], "max_items": 3},
        },
        metadata={
            "requested_mode": "war",
            "routing_context": {"domains": ["meta"], "max_items": 4},
        },
        state={
            "resolved_mode": "darbar",
            "routing_context": {"domains": ["state"], "max_items": 5},
        },
    )

    result = module.execute(context)

    assert result.outputs["knowledge_contract"].active_domains == ["state"]
    assert result.outputs["knowledge_result"]["max_items"] == 5

    sources = result.outputs["knowledge_synthesis_sources"]
    assert "context.config.routing_context" in sources
    assert "input.metadata.routing_context" in sources
    assert "run.metadata.routing_context" in sources
    assert "state.routing_context" in sources


def test_knowledge_module_normalizes_malformed_engine_payloads():
    class _MalformedEngine:
        default_max_items = 5

        def resolve_inputs(self, **kwargs):
            return {
                "active_domains": "Strategy, Risk",
                "domain_confidence": "nan",
                "max_items": "nan",
                "extra_context": {"bad": True},
                "warnings": "input-legacy-warning",
            }

        def run(self, **kwargs):
            return {
                "knowledge_contract": "bad-contract",
                "knowledge_result": {"synthesized_knowledge": "single item"},
                "warnings": "run-legacy-warning",
            }

    module = KnowledgeSynthesisModule(engine=_MalformedEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="Need advice"))
    result = module.execute(context)

    assert result.status.value == "degraded"
    assert isinstance(result.outputs["knowledge_contract"], KnowledgeContract)
    assert result.outputs["knowledge_result"]["synthesized_knowledge"] == ["single item"]
    assert "input-legacy-warning" in result.outputs["knowledge_synthesis_warnings"]
    assert "run-legacy-warning" in result.outputs["knowledge_synthesis_warnings"]


def test_knowledge_module_reads_normalized_engine_fields_and_mode_keys():
    class _VariantMalformedEngine:
        default_max_items = 5

        def resolve_inputs(self, **kwargs):
            return {
                "active-domains": ["Strategy"],
                "domain-confidence": "0.8",
                "max-items": "3",
                "extra-context": (item for item in [b"x", "x"]),
                "warnings": (item for item in [b"input-warn", "input-warn"]),
            }

        def run(self, **kwargs):
            return {
                "knowledge-contract": KnowledgeContract(
                    active_domains=["strategy"],
                    synthesized_items=["k1"],
                    trace=[],
                    quality={"candidate_quality": 0.4},
                ),
                "knowledge-result": {"synthesized_knowledge": "k1"},
                "warnings": (item for item in ["run-warn", "run-warn"]),
            }

    module = KnowledgeSynthesisModule(engine=_VariantMalformedEngine())
    context = ExecutionContext(
        input_contract=InputContract(user_input="Need advice", metadata={"requested-mode": "war"}),
        state={"routing-context": {"domains": ["state"]}},
    )
    result = module.execute(context)

    assert result.status.value == "degraded"
    assert result.outputs["knowledge_contract"].synthesized_items == ["k1"]
    assert result.outputs["knowledge_result"]["synthesized_knowledge"] == ["k1"]
    assert "input-warn" in result.outputs["knowledge_synthesis_warnings"]
    assert "run-warn" in result.outputs["knowledge_synthesis_warnings"]


def test_knowledge_module_accepts_iterable_engine_payloads():
    class _IterableMalformedEngine:
        default_max_items = 5

        def resolve_inputs(self, **kwargs):
            return [
                ("active-domains", ["strategy"]),
                ("domain-confidence", "0.7"),
                ("max-items", "4"),
                ("extra-context", [b"x", "x"]),
                ("warnings", [b"input-warn", "input-warn"]),
            ]

        def run(self, **kwargs):
            return [
                (
                    "knowledge-contract",
                    [
                        ("active_domains", ["strategy"]),
                        ("synthesized_items", ["k1"]),
                        ("trace", []),
                        ("quality", {"candidate_quality": 0.4}),
                    ],
                ),
                ("knowledge-result", [("synthesized_knowledge", ["k1"])]),
                ("warnings", [b"run-warn", "run-warn"]),
            ]

    module = KnowledgeSynthesisModule(engine=_IterableMalformedEngine())
    context = ExecutionContext(input_contract=InputContract(user_input="Need advice"))
    result = module.execute(context)

    assert result.status.value == "degraded"
    assert result.outputs["knowledge_result"]["synthesized_knowledge"] == ["k1"]
    assert "input-warn" in result.outputs["knowledge_synthesis_warnings"]
    assert "run-warn" in result.outputs["knowledge_synthesis_warnings"]


def test_knowledge_module_merges_iterable_routing_context_sources():
    module = KnowledgeSynthesisModule.create()
    context = ExecutionContext(
        input_contract=InputContract(
            user_input="Need advice",
            metadata={"routing_context": [(b"domains", ["input"])]},  # type: ignore[arg-type]
        ),
    )
    result = module.execute(context)

    assert result.outputs["knowledge_contract"].active_domains == ["input"]
    assert "input.metadata.routing_context" in result.outputs["knowledge_synthesis_sources"]


def test_knowledge_module_normalizes_partial_iterable_input_fields():
    class _FaultyDomains:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return "Risk"
            raise RuntimeError("boom")

    class _FaultyWarnings:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return "input-warn"
            raise RuntimeError("boom")

    class _PartialIterableEngine:
        default_max_items = 5

        def resolve_inputs(self, **kwargs):
            return {
                "active_domains": _FaultyDomains(),
                "domain_confidence": "0.6",
                "max_items": "3",
                "extra_context": [],
                "warnings": _FaultyWarnings(),
            }

        def run(self, **kwargs):
            return {
                "knowledge_result": {"synthesized_knowledge": []},
                "warnings": [],
            }

    module = KnowledgeSynthesisModule(engine=_PartialIterableEngine())  # type: ignore[arg-type]
    context = ExecutionContext(input_contract=InputContract(user_input="Need advice"))
    result = module.execute(context)

    assert result.outputs["knowledge_contract"].active_domains == ["risk"]
    assert "input-warn" in result.outputs["knowledge_synthesis_warnings"]


def test_knowledge_module_preserves_partial_iterable_synthesis_payload_fields():
    class _PartialWarnings:
        def __iter__(self):
            yield "run-warn"
            raise RuntimeError("warn-boom")

    class _PartialPayload(Mapping):
        def __getitem__(self, key):
            data = {
                "knowledge-result": [("synthesized_knowledge", ["k1"])],
                "warnings": _PartialWarnings(),
            }
            return data[key]

        def __iter__(self):
            yield "knowledge-result"
            yield "warnings"
            raise RuntimeError("items-boom")

        def __len__(self):
            return 2

        def items(self):
            def _items():
                yield ("knowledge-result", [("synthesized_knowledge", ["k1"])])
                yield ("warnings", _PartialWarnings())
                raise RuntimeError("items-boom")

            return _items()

    class _PartialIterableEngine:
        default_max_items = 5

        def resolve_inputs(self, **kwargs):
            return {
                "active_domains": ["strategy"],
                "domain_confidence": "0.6",
                "max_items": "3",
                "extra_context": [],
                "warnings": [],
            }

        def run(self, **kwargs):
            return _PartialPayload()

    module = KnowledgeSynthesisModule(engine=_PartialIterableEngine())  # type: ignore[arg-type]
    context = ExecutionContext(input_contract=InputContract(user_input="Need advice"))
    result = module.execute(context)

    assert result.outputs["knowledge_result"]["synthesized_knowledge"] == ["k1"]
    assert result.outputs["synthesized_knowledge"] == ["k1"]
    assert result.outputs["knowledge_synthesis_warnings"] == ["run-warn"]
