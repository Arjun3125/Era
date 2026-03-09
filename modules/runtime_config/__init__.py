"""Runtime configuration subsystem for the unified orchestration pipeline."""

from __future__ import annotations

from .engine import RuntimeConfigEngine, RuntimeConfigResult
from .module import RuntimeConfigModule


def create_runtime_config_engine() -> RuntimeConfigEngine:
    """Stable package-level factory for runtime config engine construction."""
    return RuntimeConfigEngine()


def create_runtime_config_module(
    *,
    engine: RuntimeConfigEngine | None = None,
) -> RuntimeConfigModule:
    """Stable package-level factory for runtime config module construction."""
    if engine is None:
        resolved_engine = create_runtime_config_engine()
    elif isinstance(engine, RuntimeConfigEngine):
        resolved_engine = engine
    else:
        raise TypeError("engine must be RuntimeConfigEngine when provided.")
    return RuntimeConfigModule(engine=resolved_engine)


__all__ = (
    "RuntimeConfigEngine",
    "RuntimeConfigModule",
    "RuntimeConfigResult",
    "create_runtime_config_engine",
    "create_runtime_config_module",
)
