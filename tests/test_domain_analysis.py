"""Tests for domain analysis engine and module behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.contracts import DomainAnalysisContract, ExecutionContext, InputContract
from modules.domain_analysis.engine import DomainAnalysisEngine, DomainAnalysisResult
from modules.domain_analysis.module import DomainAnalysisModule


class _FaultyRoutingPayload(Mapping):
    def __getitem__(self, key):
        data = {
            "domains": _FaultyDomains(),
            "key_entities": _FaultyEntities(),
            "llm_analysis": _FaultyAnalysisMapping(),
        }
        return data[key]

    def __iter__(self):
        yield "domains"
        yield "key_entities"
        yield "llm_analysis"
        raise RuntimeError("payload-iter-failed")

    def __len__(self) -> int:
        return 3

    def items(self):
        yield ("domains", _FaultyDomains())
        yield ("key_entities", _FaultyEntities())
        yield ("llm_analysis", _FaultyAnalysisMapping())
        raise RuntimeError("payload-items-failed")


class _FaultyDomains:
    def __iter__(self):
        yield "Strategy"
        raise RuntimeError("domains-iter-failed")


class _FaultyEntities:
    def __iter__(self):
        yield "Alice"
        raise RuntimeError("entities-iter-failed")


class _FaultyAnalysisMapping(Mapping):
    def __getitem__(self, key):
        if key == "captured_at":
            return datetime(2026, 3, 6, tzinfo=timezone.utc)
        raise KeyError(key)

    def __iter__(self):
        yield "captured_at"
        raise RuntimeError("analysis-iter-failed")

    def __len__(self) -> int:
        return 1

    def items(self):
        yield ("captured_at", datetime(2026, 3, 6, tzinfo=timezone.utc))
        raise RuntimeError("analysis-items-failed")


def test_domain_analysis_engine_normalizes_context_payload():
    engine = DomainAnalysisEngine()

    result = engine.from_routing_context(
        {
            "problem": "Need to decide whether to leave current role",
            "domains": "Strategy, career, strategy",
            "domain_scores": {
                "strategy": "1.2",
                "risk": "nan",
                "career": 0.4,
            },
            "domain_confidence": "nan",
            "stakes": "critical",
            "reversibility": True,
            "key_entities": ["Alice", "alice", "Manager"],
            "llm_analysis": {
                "captured_at": datetime(2026, 3, 4, tzinfo=timezone.utc),
                "log_path": Path("logs/domain.json"),
            },
        }
    )

    contract = result.domain_contract
    assert contract.source == "routing_context"
    assert contract.domains == ["strategy", "career"]
    assert contract.domain_confidence == 1.0
    assert contract.stakes == "high"
    assert contract.reversibility == "fully_reversible"
    assert contract.key_entities == ["Alice", "Manager"]
    assert contract.domain_scores == {"strategy": 1.0, "career": 0.4}

    analysis = result.analysis_result
    assert analysis["domain_scores"] == {"strategy": 1.0, "career": 0.4}
    assert analysis["llm_analysis"]["captured_at"].startswith("2026-03-04")
    assert analysis["llm_analysis"]["log_path"] == str(Path("logs/domain.json"))

    warnings = "\n".join(result.warnings)
    assert "Non-finite domain_scores value for 'risk' ignored." in warnings
    assert "Non-finite domain_confidence normalized to fallback." in warnings


def test_domain_analysis_engine_accepts_bytes_and_iterable_payloads():
    engine = DomainAnalysisEngine()
    result = engine.from_routing_context(
        {
            b"domains": (item for item in ["Strategy", "strategy", "Risk"]),
            "domain_scores": {b"strategy": "1.2", "risk": "-0.5"},
            "key_entities": (item for item in [b"Alice", "Alice", "Bob"]),
            "llm_error": b"timeout",
        }
    )

    assert result.domain_contract.domains == ["strategy", "risk"]
    assert result.domain_contract.domain_scores == {"strategy": 1.0, "risk": 0.0}
    assert result.domain_contract.key_entities == ["Alice", "Bob"]
    assert result.analysis_result["llm_error"] == "timeout"


def test_domain_analysis_engine_accepts_iterable_routing_context_payload():
    engine = DomainAnalysisEngine()
    result = engine.from_routing_context(
        [
            ("domains", ["Strategy", "risk"]),
            ("domain_scores", [("strategy", "1.2"), ("risk", "0.4")]),
            ("reversibility", "yes"),
        ]
    )

    assert result.domain_contract.domains == ["strategy", "risk"]
    assert result.domain_contract.domain_scores == {"strategy": 1.0, "risk": 0.4}
    assert result.domain_contract.reversibility == "fully_reversible"


def test_domain_analysis_engine_preserves_partial_iterable_values():
    engine = DomainAnalysisEngine()
    result = engine.from_routing_context(_FaultyRoutingPayload())  # type: ignore[arg-type]

    assert result.domain_contract.domains == ["strategy"]
    assert result.domain_contract.key_entities == ["Alice"]
    assert result.analysis_result["llm_analysis"]["captured_at"].startswith("2026-03-06")
    assert any("partial" in warning.lower() for warning in result.warnings)


@dataclass
class _StubEngine:
    mode: str = "routing"

    def __post_init__(self):
        self.llm_adapter = None
        self.calls = []

    def from_routing_context(self, routing_context):
        self.calls.append("routing")
        return DomainAnalysisResult(
            domain_contract=DomainAnalysisContract(
                domains=["strategy"],
                domain_confidence=0.8,
                stakes="medium",
                reversibility="partially_reversible",
                source="routing_context",
            ),
            analysis_result={"domains": ["strategy"]},
            warnings=[],
        )

    def run(self, *, user_input: str):
        self.calls.append("run")
        return DomainAnalysisResult(
            domain_contract=DomainAnalysisContract(
                domains=["career"],
                domain_confidence=0.7,
                stakes="high",
                reversibility="irreversible",
                source="domain_detector",
            ),
            analysis_result={"domains": ["career"]},
            warnings=[],
        )


def test_domain_analysis_module_prefers_routing_context_hints_when_not_forced():
    stub = _StubEngine()
    module = DomainAnalysisModule(engine=stub)

    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={
            "routing_context": {
                "domains": ["strategy"],
                "force_domain_analysis": "false",
            }
        },
        config={},
    )

    result = module.execute(context)
    assert stub.calls == ["routing"]
    assert result.outputs["domain_analysis_source"] == "routing_context"
    assert result.metrics["domain_analysis_used_routing_context"] == 1


def test_domain_analysis_module_forces_detector_path_and_fallback_on_error():
    class _RaisingEngine(_StubEngine):
        def run(self, *, user_input: str):
            self.calls.append("run")
            raise RuntimeError("detector failed")

    stub = _RaisingEngine()
    module = DomainAnalysisModule(engine=stub)

    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I leave my job?"),
        state={
            "routing_context": {
                "domains": ["strategy"],
                "force_domain_analysis": "true",
            }
        },
        config={},
    )

    result = module.execute(context)
    assert stub.calls == ["run"]
    assert result.status.value == "degraded"
    assert result.outputs["domain_analysis_source"] == "fallback"
    assert result.outputs["domain_analysis_contract"].domains == ["strategy"]
    assert result.outputs["domain_analysis_result"]["error"] == "detector failed"


def test_domain_analysis_module_invalid_int_force_toggle_does_not_force_detector():
    stub = _StubEngine()
    module = DomainAnalysisModule(engine=stub)

    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={
            "routing_context": {
                "domain": "strategy",
                "force_domain_analysis": 2,
            }
        },
        config={},
    )
    result = module.execute(context)

    assert stub.calls == ["routing"]
    assert result.outputs["domain_analysis_source"] == "routing_context"


def test_domain_analysis_module_ignores_invalid_routing_context_shape_and_uses_detector():
    stub = _StubEngine()
    module = DomainAnalysisModule(engine=stub)

    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={"routing_context": ["bad"]},
        config={},
    )
    result = module.execute(context)

    assert stub.calls == ["run"]
    assert result.outputs["domain_analysis_source"] == "domain_detector"


def test_domain_analysis_module_ignores_iterable_mapping_items_in_routing_context():
    stub = _StubEngine()
    module = DomainAnalysisModule(engine=stub)

    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={
            "routing_context": [
                {"domain": "strategy", "force_domain_analysis": False},
            ]
        },  # type: ignore[arg-type]
        config={},
    )
    result = module.execute(context)

    assert stub.calls == ["run"]
    assert result.outputs["domain_analysis_source"] == "domain_detector"


def test_domain_analysis_module_normalizes_malformed_engine_payload():
    class _MalformedEngine(_StubEngine):
        def from_routing_context(self, routing_context):
            self.calls.append("routing")
            return {
                "domain_contract": "bad-contract",
                "analysis_result": "bad-analysis",
                "warnings": "legacy-warning",
            }

    stub = _MalformedEngine()
    module = DomainAnalysisModule(engine=stub)
    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={"routing_context": {"domains": ["strategy"]}},
    )

    result = module.execute(context)
    assert stub.calls == ["routing"]
    assert result.status.value == "degraded"
    assert isinstance(result.outputs["domain_analysis_contract"], DomainAnalysisContract)
    assert result.outputs["domain_analysis_contract"].domains == ["strategy"]
    assert result.outputs["domain_analysis_result"]["domains"] == ["strategy"]
    assert "legacy-warning" in result.outputs["domain_analysis_warnings"]


def test_domain_analysis_module_reads_normalized_fields_from_engine_payload():
    class _VariantMalformedEngine(_StubEngine):
        def from_routing_context(self, routing_context):
            self.calls.append("routing")
            return {
                "domain-contract": DomainAnalysisContract(
                    domains=["career"],
                    domain_confidence=0.6,
                    stakes="medium",
                    reversibility="partially_reversible",
                    source="routing_context",
                ),
                "analysis-result": {"domains": ["career"]},
                "warnings": (item for item in ["warn", "warn", ""]),
            }

    stub = _VariantMalformedEngine()
    module = DomainAnalysisModule(engine=stub)
    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={"routing_context": {"domains": ["strategy"]}},
    )
    result = module.execute(context)

    assert stub.calls == ["routing"]
    assert result.outputs["domain_analysis_contract"].domains == ["career"]
    assert result.outputs["domain_analysis_result"]["domains"] == ["career"]
    assert result.outputs["domain_analysis_warnings"] == ["warn"]


def test_domain_analysis_module_accepts_iterable_engine_payload():
    class _IterableMalformedEngine(_StubEngine):
        def from_routing_context(self, routing_context):
            self.calls.append("routing")
            return [
                (
                    "domain-contract",
                    [
                        ("domains", ["finance"]),
                        ("domain_confidence", "0.6"),
                        ("stakes", "critical"),
                        ("reversibility", "reversible"),
                    ],
                ),
                ("analysis-result", [("domains", ["finance"])]),
                ("warnings", [b"warn", "warn"]),
            ]

    stub = _IterableMalformedEngine()
    module = DomainAnalysisModule(engine=stub)
    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={"routing_context": {"domains": ["strategy"]}},
    )
    result = module.execute(context)

    assert stub.calls == ["routing"]
    assert result.outputs["domain_analysis_contract"].domains == ["finance"]
    assert result.outputs["domain_analysis_contract"].stakes == "high"
    assert result.outputs["domain_analysis_contract"].reversibility == "fully_reversible"
    assert result.outputs["domain_analysis_result"]["domains"] == ["finance"]
    assert result.outputs["domain_analysis_warnings"] == ["warn"]


def test_domain_analysis_module_preserves_partial_iterable_engine_payload():
    class _PartialWarnings:
        def __iter__(self):
            yield "warn-a"
            yield "warn-b"
            raise RuntimeError("warnings-iter-failed")

    class _PartialPayload(Mapping):
        def __getitem__(self, key):
            data = {
                "domain-contract": DomainAnalysisContract(
                    domains=["finance"],
                    domain_confidence=0.6,
                    stakes="high",
                    reversibility="fully_reversible",
                    source="routing_context",
                ),
                "analysis-result": [("domains", ["finance"]), ("domain_confidence", "0.6")],
                "warnings": _PartialWarnings(),
            }
            return data[key]

        def __iter__(self):
            yield "domain-contract"
            yield "analysis-result"
            yield "warnings"
            raise RuntimeError("payload-iter-failed")

        def __len__(self) -> int:
            return 3

        def items(self):
            yield (
                "domain-contract",
                DomainAnalysisContract(
                    domains=["finance"],
                    domain_confidence=0.6,
                    stakes="high",
                    reversibility="fully_reversible",
                    source="routing_context",
                ),
            )
            yield ("analysis-result", [("domains", ["finance"]), ("domain_confidence", "0.6")])
            yield ("warnings", _PartialWarnings())
            raise RuntimeError("payload-items-failed")

    class _PartialEngine(_StubEngine):
        def from_routing_context(self, routing_context):
            self.calls.append("routing")
            return _PartialPayload()

    stub = _PartialEngine()
    module = DomainAnalysisModule(engine=stub)
    context = ExecutionContext(
        input_contract=InputContract(user_input="Should I move teams?"),
        state={"routing_context": {"domains": ["strategy"]}},
    )

    result = module.execute(context)

    assert stub.calls == ["routing"]
    assert result.outputs["domain_analysis_contract"].domains == ["finance"]
    assert result.outputs["domain_analysis_result"]["domains"] == ["finance"]
    assert result.outputs["domain_analysis_warnings"] == ["warn-a", "warn-b"]
