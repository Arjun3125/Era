"""Tests for top-level core package exports."""

from __future__ import annotations

from core import ErrorPolicy, PipelineOrchestrator, RunStatus, create_orchestrator


def test_core_package_exposes_orchestrator_factory_and_enums():
    orchestrator = create_orchestrator(name="core.pkg", strict=True)
    assert isinstance(orchestrator, PipelineOrchestrator)
    assert orchestrator.name == "core.pkg"
    assert orchestrator.strict is True

    assert RunStatus.COMPLETED.value == "completed"
    assert ErrorPolicy.DEGRADE.value == "degrade"
