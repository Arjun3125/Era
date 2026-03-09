"""Tests for council_execution package-level factories."""

from __future__ import annotations

from modules.council_execution import (
    CouncilExecutionEngine,
    CouncilExecutionModule,
    create_council_execution_engine,
    create_council_execution_module,
)
from modules.council_router.mode_orchestrator import ExecutionConfig


def test_council_execution_package_engine_factory():
    config = ExecutionConfig(disable_kis=True)
    engine = create_council_execution_engine(llm="llm", config=config)
    assert isinstance(engine, CouncilExecutionEngine)
    assert engine.llm == "llm"
    assert engine.orchestrator.config is config


def test_council_execution_package_module_factory_with_engine():
    engine = create_council_execution_engine(llm="x")
    module = create_council_execution_module(engine=engine)
    assert isinstance(module, CouncilExecutionModule)
    assert module.engine is engine


def test_council_execution_package_module_factory_constructs_engine():
    module = create_council_execution_module(llm="y")
    assert isinstance(module, CouncilExecutionModule)
    assert isinstance(module.engine, CouncilExecutionEngine)
    assert module.engine.llm == "y"
