"""Tests for contract_validation package-level factories."""

from __future__ import annotations

from modules.contract_validation import (
    ContractValidationEngine,
    ContractValidationModule,
    create_contract_validation_engine,
    create_contract_validation_module,
)


def test_contract_validation_package_engine_factory():
    engine = create_contract_validation_engine()
    assert isinstance(engine, ContractValidationEngine)


def test_contract_validation_package_module_factory_with_engine():
    engine = ContractValidationEngine()
    module = create_contract_validation_module(engine=engine)
    assert isinstance(module, ContractValidationModule)
    assert module.engine is engine


def test_contract_validation_package_module_factory_constructs_engine():
    module = create_contract_validation_module()
    assert isinstance(module, ContractValidationModule)
    assert isinstance(module.engine, ContractValidationEngine)
