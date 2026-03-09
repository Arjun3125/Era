"""Tests for council_normalization package-level factories."""

from __future__ import annotations

from modules.council_normalization import (
    CouncilNormalizationEngine,
    CouncilNormalizationModule,
    create_council_normalization_engine,
    create_council_normalization_module,
)


def test_council_normalization_package_engine_factory():
    engine = create_council_normalization_engine()
    assert isinstance(engine, CouncilNormalizationEngine)


def test_council_normalization_package_module_factory_with_engine():
    engine = CouncilNormalizationEngine()
    module = create_council_normalization_module(engine=engine)
    assert isinstance(module, CouncilNormalizationModule)
    assert module.engine is engine


def test_council_normalization_package_module_factory_constructs_engine():
    module = create_council_normalization_module()
    assert isinstance(module, CouncilNormalizationModule)
    assert isinstance(module.engine, CouncilNormalizationEngine)
