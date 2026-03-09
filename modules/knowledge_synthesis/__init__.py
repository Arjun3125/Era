"""Knowledge synthesis subsystem for orchestrator-driven retrieval."""

from __future__ import annotations

from .engine import KnowledgeSynthesisEngine, KnowledgeSynthesisInputs, KnowledgeSynthesisResult
from .module import KnowledgeSynthesisModule


def create_knowledge_synthesis_engine() -> KnowledgeSynthesisEngine:
    """Stable package-level factory for knowledge synthesis engine construction."""
    return KnowledgeSynthesisEngine()


def create_knowledge_synthesis_module(
    *,
    engine: KnowledgeSynthesisEngine | None = None,
) -> KnowledgeSynthesisModule:
    """Stable package-level factory for knowledge synthesis module construction."""
    return KnowledgeSynthesisModule(engine=engine or create_knowledge_synthesis_engine())


__all__ = (
    "KnowledgeSynthesisEngine",
    "KnowledgeSynthesisInputs",
    "KnowledgeSynthesisModule",
    "KnowledgeSynthesisResult",
    "create_knowledge_synthesis_engine",
    "create_knowledge_synthesis_module",
)
