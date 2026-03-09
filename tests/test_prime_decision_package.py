"""Tests for prime decision package-level factories."""

from __future__ import annotations

from modules.prime_decision import (
    PrimeDecisionEngine,
    PrimeDecisionModule,
    create_prime_decision_engine,
    create_prime_decision_module,
)


def test_prime_decision_package_engine_factory():
    engine = create_prime_decision_engine(risk_threshold=0.55, llm_adapter="llm")
    assert isinstance(engine, PrimeDecisionEngine)
    assert engine.risk_threshold == 0.55
    assert engine.llm_adapter == "llm"


def test_prime_decision_package_module_factory_uses_provided_engine():
    engine = PrimeDecisionEngine(risk_threshold=0.33)
    module = create_prime_decision_module(engine=engine)
    assert isinstance(module, PrimeDecisionModule)
    assert module.engine is engine


def test_prime_decision_package_module_factory_constructs_engine_when_missing():
    module = create_prime_decision_module(risk_threshold=0.44, llm_adapter="x")
    assert isinstance(module, PrimeDecisionModule)
    assert module.engine.risk_threshold == 0.44
    assert module.engine.llm_adapter == "x"
