"""Compatibility facade for mode-aware council orchestration.

This module preserves the historical import path:
`persona.council.dynamic_council`.

Implementation has moved to:
`modules.council_router.dynamic_council`.
"""

from modules.council_router.dynamic_council import DynamicCouncil

__all__ = ["DynamicCouncil"]

