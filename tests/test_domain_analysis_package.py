"""Tests for domain_analysis package-level factories."""

from __future__ import annotations

from modules.domain_analysis import (
    DomainAnalysisEngine,
    DomainAnalysisModule,
    create_domain_analysis_engine,
    create_domain_analysis_module,
)


def test_domain_analysis_package_engine_factory():
    engine = create_domain_analysis_engine(llm_adapter="llm")
    assert isinstance(engine, DomainAnalysisEngine)
    assert engine.llm_adapter == "llm"


def test_domain_analysis_package_module_factory_with_engine():
    engine = DomainAnalysisEngine(llm_adapter="x")
    module = create_domain_analysis_module(engine=engine)
    assert isinstance(module, DomainAnalysisModule)
    assert module.engine is engine


def test_domain_analysis_package_module_factory_constructs_engine():
    module = create_domain_analysis_module(llm_adapter="y")
    assert isinstance(module, DomainAnalysisModule)
    assert isinstance(module.engine, DomainAnalysisEngine)
    assert module.engine.llm_adapter == "y"
