"""Domain modules used by the unified orchestration pipeline."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict


MODULE_PACKAGE_NAMES = (
    "contract_validation",
    "council_execution",
    "council_normalization",
    "council_router",
    "decision_packaging",
    "decision_pipeline",
    "domain_analysis",
    "input_normalization",
    "knowledge_synthesis",
    "scenario_memory",
    "prime_decision",
    "runtime_config",
)

_LAZY_EXPORTS = {
    "DecisionPipelineEngine": "modules.decision_pipeline",
    "DecisionPipelineModule": "modules.decision_pipeline",
    "DecisionPipelineResult": "modules.decision_pipeline",
    "create_decision_pipeline": "modules.decision_pipeline",
}


def get_module_catalog() -> Dict[str, str]:
    """Return canonical package paths for registered orchestration modules."""
    return {name: f"modules.{name}" for name in MODULE_PACKAGE_NAMES}


def __getattr__(name: str) -> Any:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'modules' has no attribute '{name}'")
    module = import_module(module_path)
    return getattr(module, name)


__all__ = (
    "DecisionPipelineEngine",
    "DecisionPipelineModule",
    "DecisionPipelineResult",
    "MODULE_PACKAGE_NAMES",
    "create_decision_pipeline",
    "get_module_catalog",
)
