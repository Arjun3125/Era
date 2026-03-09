"""Tests for runtime_config package-level factories."""

from __future__ import annotations

import pytest

from modules.runtime_config import (
    RuntimeConfigEngine,
    RuntimeConfigModule,
    create_runtime_config_engine,
    create_runtime_config_module,
)


def test_runtime_config_package_engine_factory():
    engine = create_runtime_config_engine()
    assert isinstance(engine, RuntimeConfigEngine)


def test_runtime_config_package_module_factory_with_provided_engine():
    engine = RuntimeConfigEngine()
    module = create_runtime_config_module(engine=engine)
    assert isinstance(module, RuntimeConfigModule)
    assert module.engine is engine


def test_runtime_config_package_module_factory_constructs_engine_when_missing():
    module = create_runtime_config_module()
    assert isinstance(module, RuntimeConfigModule)
    assert isinstance(module.engine, RuntimeConfigEngine)


def test_runtime_config_package_module_factory_rejects_invalid_engine():
    with pytest.raises(TypeError, match="RuntimeConfigEngine"):
        create_runtime_config_module(engine=object())  # type: ignore[arg-type]
