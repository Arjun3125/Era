"""Tests for orchestrator package exports and factory."""

from __future__ import annotations

import pytest

from core.orchestrator import ErrorPolicy, RunStatus, create_orchestrator
from core.orchestrator.runtime import PipelineOrchestrator


def test_package_factory_builds_pipeline_orchestrator():
    orchestrator = create_orchestrator(name="pkg.test", strict=True)
    assert isinstance(orchestrator, PipelineOrchestrator)
    assert orchestrator.name == "pkg.test"
    assert orchestrator.strict is True


def test_runtime_enums_exposed_from_package():
    assert RunStatus.COMPLETED.value == "completed"
    assert ErrorPolicy.ABORT.value == "abort"


def test_package_factory_normalizes_name_and_strict_inputs():
    orchestrator = create_orchestrator(name=b" pkg.bytes ", strict="1")  # type: ignore[arg-type]
    assert orchestrator.name == "pkg.bytes"
    assert orchestrator.strict is True

    default_name_orchestrator = create_orchestrator(name=" ", strict=b"0")  # type: ignore[arg-type]
    assert default_name_orchestrator.name == "era_pipeline"
    assert default_name_orchestrator.strict is False


def test_package_factory_rejects_invalid_strict_values():
    with pytest.raises(TypeError, match="strict must be a boolean"):
        create_orchestrator(strict="maybe")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="strict must be a boolean"):
        create_orchestrator(strict=2)  # type: ignore[arg-type]
