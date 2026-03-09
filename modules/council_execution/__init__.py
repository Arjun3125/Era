"""Council execution subsystem for mode-aware minister deliberation."""

from __future__ import annotations

from typing import Any

from modules.council_router.mode_orchestrator import ExecutionConfig

from .engine import CouncilExecutionEngine
from .module import CouncilExecutionModule


def create_council_execution_engine(
    *,
    llm: Any = None,
    config: ExecutionConfig | None = None,
) -> CouncilExecutionEngine:
    """Stable package-level factory for council execution engine construction."""
    return CouncilExecutionEngine.create(
        llm=llm,
        config=config,
    )


def create_council_execution_module(
    *,
    engine: CouncilExecutionEngine | None = None,
    llm: Any = None,
    config: ExecutionConfig | None = None,
) -> CouncilExecutionModule:
    """Stable package-level factory for council execution module construction."""
    resolved_engine = engine or create_council_execution_engine(llm=llm, config=config)
    return CouncilExecutionModule(engine=resolved_engine)


__all__ = (
    "CouncilExecutionEngine",
    "CouncilExecutionModule",
    "create_council_execution_engine",
    "create_council_execution_module",
)
