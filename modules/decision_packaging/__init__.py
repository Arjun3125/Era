"""Decision packaging subsystem for unified decision pipeline."""

from __future__ import annotations

from .engine import DecisionPackagingEngine, DecisionPackagingResult
from .module import DecisionPackagingModule


def create_decision_packaging_engine() -> DecisionPackagingEngine:
    """Stable package-level factory for decision packaging engine construction."""
    return DecisionPackagingEngine()


def create_decision_packaging_module(
    *,
    engine: DecisionPackagingEngine | None = None,
) -> DecisionPackagingModule:
    """Stable package-level factory for decision packaging module construction."""
    return DecisionPackagingModule(engine=engine or create_decision_packaging_engine())


__all__ = (
    "DecisionPackagingEngine",
    "DecisionPackagingModule",
    "DecisionPackagingResult",
    "create_decision_packaging_engine",
    "create_decision_packaging_module",
)
