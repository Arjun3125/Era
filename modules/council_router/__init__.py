"""Council routing subsystem for mode resolution and council orchestration."""

from __future__ import annotations

from typing import Any

from .mode_orchestrator import (
    DarbarModeStrategy,
    ExecutionConfig,
    MeetingModeStrategy,
    ModeOrchestrator,
    ModeResponse,
    ModeStrategy,
    QuickModeStrategy,
    UncertaintyPolicyConfig,
    WarModeStrategy,
)
from .engine import ModeRoutingEngine, ModeRoutingResult


def create_mode_routing_engine(
    *,
    orchestrator: ModeOrchestrator | None = None,
    config: ExecutionConfig | None = None,
    default_mode: str = "meeting",
) -> ModeRoutingEngine:
    """Stable package-level factory for mode routing engine construction."""
    resolved_orchestrator = orchestrator or ModeOrchestrator(config=config)
    return ModeRoutingEngine(
        orchestrator=resolved_orchestrator,
        default_mode=default_mode,
    )


def create_mode_routing_module(
    *,
    engine: ModeRoutingEngine | None = None,
    orchestrator: ModeOrchestrator | None = None,
    config: ExecutionConfig | None = None,
    default_mode: str = "meeting",
) -> Any:
    """Stable package-level factory for mode routing module construction."""
    from .module import ModeRoutingModule

    resolved_engine = engine or create_mode_routing_engine(
        orchestrator=orchestrator,
        config=config,
        default_mode=default_mode,
    )
    return ModeRoutingModule(
        orchestrator=resolved_engine.orchestrator,
        engine=resolved_engine,
    )


__all__ = (
    "DarbarModeStrategy",
    "ExecutionConfig",
    "MeetingModeStrategy",
    "ModeOrchestrator",
    "ModeResponse",
    "ModeStrategy",
    "QuickModeStrategy",
    "UncertaintyPolicyConfig",
    "WarModeStrategy",
    "ModeRoutingEngine",
    "ModeRoutingResult",
    "DynamicCouncil",
    "ModeRoutingModule",
    "create_mode_routing_engine",
    "create_mode_routing_module",
)


def __getattr__(name: str) -> Any:
    """Lazy exports to avoid import cycles during staged migration."""
    if name == "DynamicCouncil":
        from .dynamic_council import DynamicCouncil

        return DynamicCouncil
    if name == "ModeRoutingModule":
        from .module import ModeRoutingModule

        return ModeRoutingModule
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
