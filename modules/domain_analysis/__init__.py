"""Domain analysis subsystem for decision pipeline routing context."""

from __future__ import annotations

from typing import Any

from .engine import DomainAnalysisEngine, DomainAnalysisResult
from .module import DomainAnalysisModule


def create_domain_analysis_engine(
    *,
    llm_adapter: Any = None,
) -> DomainAnalysisEngine:
    """Stable package-level factory for domain analysis engine construction."""
    return DomainAnalysisEngine(llm_adapter=llm_adapter)


def create_domain_analysis_module(
    *,
    engine: DomainAnalysisEngine | None = None,
    llm_adapter: Any = None,
) -> DomainAnalysisModule:
    """Stable package-level factory for domain analysis module construction."""
    resolved_engine = engine or create_domain_analysis_engine(llm_adapter=llm_adapter)
    return DomainAnalysisModule(engine=resolved_engine)


__all__ = (
    "DomainAnalysisEngine",
    "DomainAnalysisModule",
    "DomainAnalysisResult",
    "create_domain_analysis_engine",
    "create_domain_analysis_module",
)
