"""Prime decision subsystem for final authority and decision contracts."""

from __future__ import annotations

from typing import Any

from .engine import PrimeDecisionEngine, PrimeDecisionResult
from .module import PrimeDecisionModule


def create_prime_decision_engine(
    *,
    risk_threshold: float = 0.7,
    llm_adapter: Any = None,
    prime_decider: Any = None,
) -> PrimeDecisionEngine:
    """Stable package-level factory for Prime decision engine construction."""
    return PrimeDecisionEngine(
        risk_threshold=risk_threshold,
        llm_adapter=llm_adapter,
        prime_decider=prime_decider,
    )


def create_prime_decision_module(
    *,
    engine: PrimeDecisionEngine | None = None,
    risk_threshold: float = 0.7,
    llm_adapter: Any = None,
    prime_decider: Any = None,
) -> PrimeDecisionModule:
    """Stable package-level factory for Prime decision module construction."""
    resolved_engine = engine or create_prime_decision_engine(
        risk_threshold=risk_threshold,
        llm_adapter=llm_adapter,
        prime_decider=prime_decider,
    )
    return PrimeDecisionModule(engine=resolved_engine)


__all__ = (
    "PrimeDecisionEngine",
    "PrimeDecisionModule",
    "PrimeDecisionResult",
    "create_prime_decision_engine",
    "create_prime_decision_module",
)
