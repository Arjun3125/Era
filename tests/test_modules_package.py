"""Tests for top-level modules package API and lazy exports."""

from __future__ import annotations

import pytest

import modules


def test_modules_catalog_matches_registered_package_names():
    catalog = modules.get_module_catalog()
    assert isinstance(catalog, dict)
    assert set(catalog.keys()) == set(modules.MODULE_PACKAGE_NAMES)
    assert catalog["decision_pipeline"] == "modules.decision_pipeline"


def test_modules_package_lazy_exports_decision_pipeline_symbols():
    assert modules.DecisionPipelineEngine.__name__ == "DecisionPipelineEngine"
    assert modules.DecisionPipelineModule.__name__ == "DecisionPipelineModule"
    assert modules.DecisionPipelineResult.__name__ == "DecisionPipelineResult"
    assert callable(modules.create_decision_pipeline)


def test_modules_package_unknown_attribute_raises():
    with pytest.raises(AttributeError, match="has no attribute"):
        getattr(modules, "NonExistingExport")
