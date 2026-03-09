"""Input normalization subsystem for unified orchestrated execution."""

from __future__ import annotations

from .engine import InputNormalizationEngine, InputNormalizationResult
from .module import InputNormalizationModule


def create_input_normalization_engine(
    *,
    default_mode: str = "meeting",
) -> InputNormalizationEngine:
    """Stable package-level factory for input normalization engine construction."""
    return InputNormalizationEngine(default_mode=default_mode)


def create_input_normalization_module(
    *,
    engine: InputNormalizationEngine | None = None,
    default_mode: str = "meeting",
) -> InputNormalizationModule:
    """Stable package-level factory for input normalization module construction."""
    resolved_engine = engine or create_input_normalization_engine(default_mode=default_mode)
    return InputNormalizationModule(engine=resolved_engine)


__all__ = (
    "InputNormalizationEngine",
    "InputNormalizationModule",
    "InputNormalizationResult",
    "create_input_normalization_engine",
    "create_input_normalization_module",
)
