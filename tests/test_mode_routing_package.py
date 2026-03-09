"""Tests for council_router package-level factories."""

from __future__ import annotations

from modules.council_router import (
    ExecutionConfig,
    ModeOrchestrator,
    ModeRoutingEngine,
    create_mode_routing_engine,
    create_mode_routing_module,
)


def test_mode_routing_package_engine_factory():
    orchestrator = ModeOrchestrator(config=ExecutionConfig(disable_kis=True))
    engine = create_mode_routing_engine(orchestrator=orchestrator, default_mode="quick")
    assert isinstance(engine, ModeRoutingEngine)
    assert engine.orchestrator is orchestrator
    assert engine.default_mode == "quick"


def test_mode_routing_package_module_factory_with_engine():
    engine = create_mode_routing_engine(default_mode="war")
    module = create_mode_routing_module(engine=engine)
    assert module.engine is engine
    assert module.orchestrator is engine.orchestrator


def test_mode_routing_package_module_factory_constructs_engine_from_config():
    config = ExecutionConfig(disable_pwm=True)
    module = create_mode_routing_module(config=config, default_mode="meeting")
    assert isinstance(module.engine, ModeRoutingEngine)
    assert module.engine.orchestrator.config is config
    assert module.engine.default_mode == "meeting"
