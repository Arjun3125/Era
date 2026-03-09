"""Tests for knowledge_synthesis package-level factories."""

from __future__ import annotations

from modules.knowledge_synthesis import (
    KnowledgeSynthesisEngine,
    KnowledgeSynthesisModule,
    create_knowledge_synthesis_engine,
    create_knowledge_synthesis_module,
)


def test_knowledge_synthesis_package_engine_factory():
    engine = create_knowledge_synthesis_engine()
    assert isinstance(engine, KnowledgeSynthesisEngine)


def test_knowledge_synthesis_package_module_factory_with_engine():
    engine = KnowledgeSynthesisEngine(default_max_items=5)
    module = create_knowledge_synthesis_module(engine=engine)
    assert isinstance(module, KnowledgeSynthesisModule)
    assert module.engine is engine


def test_knowledge_synthesis_package_module_factory_constructs_engine():
    module = create_knowledge_synthesis_module()
    assert isinstance(module, KnowledgeSynthesisModule)
    assert isinstance(module.engine, KnowledgeSynthesisEngine)
