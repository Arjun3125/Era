"""Compatibility facade for mode routing.

This module preserves the historical import path:
`persona.modes.mode_orchestrator`.

Implementation has moved to:
`modules.council_router.mode_orchestrator`.
"""

from modules.council_router.mode_orchestrator import (
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

__all__ = [
    "ExecutionConfig",
    "UncertaintyPolicyConfig",
    "ModeResponse",
    "ModeStrategy",
    "QuickModeStrategy",
    "WarModeStrategy",
    "MeetingModeStrategy",
    "DarbarModeStrategy",
    "ModeOrchestrator",
]

