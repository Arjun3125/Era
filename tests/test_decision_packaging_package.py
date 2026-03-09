"""Tests for decision_packaging package-level factories."""

from __future__ import annotations

from modules.decision_packaging import (
    DecisionPackagingEngine,
    DecisionPackagingModule,
    create_decision_packaging_engine,
    create_decision_packaging_module,
)


def test_decision_packaging_package_engine_factory():
    engine = create_decision_packaging_engine()
    assert isinstance(engine, DecisionPackagingEngine)


def test_decision_packaging_package_module_factory_with_engine():
    engine = DecisionPackagingEngine()
    module = create_decision_packaging_module(engine=engine)
    assert isinstance(module, DecisionPackagingModule)
    assert module.engine is engine


def test_decision_packaging_package_module_factory_constructs_engine():
    module = create_decision_packaging_module()
    assert isinstance(module, DecisionPackagingModule)
    assert isinstance(module.engine, DecisionPackagingEngine)
