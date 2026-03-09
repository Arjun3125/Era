"""
Evaluation package exports (lazy-loaded to avoid heavy import side effects).
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "EvaluationRunner",
    "EvaluationConfig",
    "StatsEngine",
    "ConfidenceInterval",
    "OutcomeScorer",
    "RegretScorer",
    "RubricEngine",
]


def __getattr__(name: str) -> Any:
    if name in {"EvaluationRunner", "EvaluationConfig"}:
        mod = import_module("evaluation.evaluation_runner")
        return getattr(mod, name)
    if name in {"StatsEngine", "ConfidenceInterval"}:
        mod = import_module("evaluation.stats_engine")
        return getattr(mod, name)
    if name == "OutcomeScorer":
        mod = import_module("evaluation.scoring.outcome_scorer")
        return getattr(mod, name)
    if name == "RegretScorer":
        mod = import_module("evaluation.scoring.regret_scorer")
        return getattr(mod, name)
    if name == "RubricEngine":
        mod = import_module("evaluation.scoring.rubric_engine")
        return getattr(mod, name)
    raise AttributeError(name)
