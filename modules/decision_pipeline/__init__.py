"""Unified MCA decision pipeline composed of mode, council, and prime modules."""

from __future__ import annotations

import math
from typing import Any

from .engine import DecisionPipelineEngine, DecisionPipelineResult
from .errors import DecisionPipelineErrorEngine, DecisionPipelineErrorResult
from .extensions import ExtensionStagePlanner, ExtensionStageSpec
from .module import DecisionPipelineModule
from .telemetry import DecisionPipelineTelemetryEngine, DecisionPipelineTelemetryResult


def create_decision_pipeline(
    *,
    llm: Any = None,
    prime_decider: Any = None,
    risk_threshold: float = 0.7,
    strict: bool = False,
) -> DecisionPipelineEngine:
    """Stable package-level factory for central decision pipeline construction."""
    normalized_risk_threshold = _normalize_risk_threshold(risk_threshold)
    normalized_strict = _normalize_strict(strict)
    return DecisionPipelineEngine.create(
        llm=llm,
        prime_decider=prime_decider,
        risk_threshold=normalized_risk_threshold,
        strict=normalized_strict,
    )


def _normalize_risk_threshold(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("risk_threshold must be a finite float between 0.0 and 1.0.")
    if isinstance(value, (bytes, bytearray)):
        value = _normalize_text(value)
    try:
        numeric = float(value)
    except Exception as exc:
        raise TypeError("risk_threshold must be a finite float between 0.0 and 1.0.") from exc
    if not math.isfinite(numeric):
        raise ValueError("risk_threshold must be finite.")
    if numeric < 0.0 or numeric > 1.0:
        raise ValueError("risk_threshold must be between 0.0 and 1.0.")
    return numeric


def _normalize_strict(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise ValueError("strict must be a boolean or equivalent 0/1 value.")
    if isinstance(value, (bytes, bytearray)):
        value = _normalize_text(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        raise ValueError("strict must be a boolean or equivalent 0/1 value.")
    raise TypeError("strict must be a boolean or equivalent 0/1 value.")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


__all__ = (
    "DecisionPipelineEngine",
    "DecisionPipelineErrorEngine",
    "DecisionPipelineErrorResult",
    "DecisionPipelineModule",
    "DecisionPipelineResult",
    "ExtensionStagePlanner",
    "ExtensionStageSpec",
    "DecisionPipelineTelemetryEngine",
    "DecisionPipelineTelemetryResult",
    "create_decision_pipeline",
)
