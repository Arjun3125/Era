"""Tests for input_normalization package-level factories."""

from __future__ import annotations

from modules.input_normalization import (
    InputNormalizationEngine,
    InputNormalizationModule,
    create_input_normalization_engine,
    create_input_normalization_module,
)


def test_input_normalization_package_engine_factory():
    engine = create_input_normalization_engine(default_mode="war")
    assert isinstance(engine, InputNormalizationEngine)
    assert engine.default_mode == "war"


def test_input_normalization_package_module_factory_with_engine():
    engine = InputNormalizationEngine(default_mode="quick")
    module = create_input_normalization_module(engine=engine)
    assert isinstance(module, InputNormalizationModule)
    assert module.engine is engine


def test_input_normalization_package_module_factory_constructs_engine():
    module = create_input_normalization_module(default_mode="darbar")
    assert isinstance(module, InputNormalizationModule)
    assert isinstance(module.engine, InputNormalizationEngine)
    assert module.engine.default_mode == "darbar"
