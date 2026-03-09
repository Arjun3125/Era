"""Central pipeline runtime for unified staged orchestration."""

from __future__ import annotations

from typing import Any

from .runtime import (
    ErrorPolicy,
    OrchestrationResult,
    PipelineOrchestrator,
    RunStatus,
    StageOutcome,
)


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _coerce_name(value: Any) -> str:
    text = _normalize_text(value)
    return text or "era_pipeline"


def _coerce_strict_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise TypeError("strict must be a boolean.")
    text = _normalize_text(value).lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    raise TypeError("strict must be a boolean.")


def create_orchestrator(*, name: Any = "era_pipeline", strict: Any = False) -> PipelineOrchestrator:
    """Stable package-level factory for pipeline orchestrator construction."""
    return PipelineOrchestrator(
        name=_coerce_name(name),
        strict=_coerce_strict_flag(strict),
    )


__all__ = (
    "ErrorPolicy",
    "OrchestrationResult",
    "PipelineOrchestrator",
    "RunStatus",
    "StageOutcome",
    "create_orchestrator",
)
