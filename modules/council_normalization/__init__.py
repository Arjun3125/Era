"""Council normalization subsystem for unified decision pipeline."""

from __future__ import annotations

from .engine import CouncilNormalizationEngine, CouncilNormalizationResult
from .module import CouncilNormalizationModule


def create_council_normalization_engine() -> CouncilNormalizationEngine:
    """Stable package-level factory for council normalization engine construction."""
    return CouncilNormalizationEngine()


def create_council_normalization_module(
    *,
    engine: CouncilNormalizationEngine | None = None,
) -> CouncilNormalizationModule:
    """Stable package-level factory for council normalization module construction."""
    return CouncilNormalizationModule(engine=engine or create_council_normalization_engine())


__all__ = (
    "CouncilNormalizationEngine",
    "CouncilNormalizationModule",
    "CouncilNormalizationResult",
    "create_council_normalization_engine",
    "create_council_normalization_module",
)
