"""Contract validation subsystem for unified orchestrated decision flow."""

from __future__ import annotations

from .engine import ContractValidationEngine, ContractValidationResult
from .module import ContractValidationModule


def create_contract_validation_engine() -> ContractValidationEngine:
    """Stable package-level factory for contract validation engine construction."""
    return ContractValidationEngine()


def create_contract_validation_module(
    *,
    engine: ContractValidationEngine | None = None,
) -> ContractValidationModule:
    """Stable package-level factory for contract validation module construction."""
    return ContractValidationModule(engine=engine or create_contract_validation_engine())


__all__ = (
    "ContractValidationEngine",
    "ContractValidationModule",
    "ContractValidationResult",
    "create_contract_validation_engine",
    "create_contract_validation_module",
)
