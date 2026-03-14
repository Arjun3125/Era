"""
Mode orchestration system for Persona.

Controls decision pipeline based on conversation mode:
- quick: Direct 1:1 mentoring (no council)
- war: Victory-focused (Risk + Power + Strategy)
- meeting: Structured debate (3-5 relevant ministers)
- darbar: Full council wisdom (all 19 ministers)
"""

from .mode_orchestrator import (
    ModeOrchestrator,
    ModeResponse,
    ModeStrategy,
    QuickModeStrategy,
    WarModeStrategy,
    MeetingModeStrategy,
    DarbarModeStrategy,
)

from .mode_metrics import ModeMetrics

__all__ = [
    "ModeOrchestrator",
    "ModeResponse",
    "ModeStrategy",
    "QuickModeStrategy",
    "WarModeStrategy",
    "MeetingModeStrategy",
    "DarbarModeStrategy",
    "ModeMetrics",
]
