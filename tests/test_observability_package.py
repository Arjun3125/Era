"""Tests for core.observability package-level factories."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from config import RuntimeSettings
from core.observability import (
    EventTraceBuilder,
    OrchestrationMetrics,
    StructuredEventLogger,
    create_metrics_builder,
    create_structured_logger,
    create_trace_builder,
)


def test_observability_package_factories_return_expected_types():
    assert isinstance(create_metrics_builder(), OrchestrationMetrics)
    assert isinstance(create_trace_builder(), EventTraceBuilder)

    settings = RuntimeSettings(
        observability_enabled=True,
        observability_write_file=False,
        observability_stderr=False,
    )
    assert isinstance(create_structured_logger(settings), StructuredEventLogger)


def test_observability_package_logger_factory_validates_settings_type():
    with pytest.raises(TypeError, match="settings must be RuntimeSettings"):
        create_structured_logger(object())  # type: ignore[arg-type]


def test_observability_package_logger_factory_accepts_mapping_settings():
    logger = create_structured_logger(
        {
            "obs_enabled": True,
            "obs_write_file": False,
            "obs_stderr": False,
        }
    )
    assert isinstance(logger, StructuredEventLogger)
    assert logger.settings.observability_enabled is True


def test_observability_package_logger_factory_accepts_iterable_key_value_settings():
    logger = create_structured_logger(
        [
            ("obs_enabled", True),
            ("obs_write_file", False),
            ("obs_stderr", False),
        ]
    )
    assert isinstance(logger, StructuredEventLogger)
    assert logger.settings.observability_stderr is False


def test_observability_package_logger_factory_rejects_bad_iterable_shape():
    with pytest.raises(TypeError, match="key-value pairs"):
        create_structured_logger([("obs_enabled", True, "unexpected")])  # type: ignore[arg-type]


def test_observability_package_logger_factory_rejects_unhashable_iterable_keys():
    with pytest.raises(TypeError, match="keys must be hashable"):
        create_structured_logger([(["obs_enabled"], True)])  # type: ignore[arg-type]


def test_observability_package_logger_factory_preserves_partial_faulty_iterable():
    class _FaultyIterable:
        def __iter__(self):
            return self

        def __next__(self):
            if not hasattr(self, "_seen"):
                self._seen = True
                return ("obs_enabled", True)
            raise RuntimeError("boom")

    logger = create_structured_logger(_FaultyIterable())  # type: ignore[arg-type]
    assert isinstance(logger, StructuredEventLogger)
    assert logger.settings.observability_enabled is True


def test_observability_package_logger_factory_preserves_partial_faulty_mapping():
    class _FaultyMapping(Mapping):
        def __getitem__(self, key):
            data = {
                "obs_enabled": True,
                "obs_write_file": False,
                "obs_stderr": False,
            }
            return data[key]

        def __iter__(self):
            yield "obs_enabled"
            yield "obs_write_file"
            yield "obs_stderr"
            raise RuntimeError("mapping-iter-failed")

        def __len__(self):
            return 3

        def items(self):
            yield ("obs_enabled", True)
            yield ("obs_write_file", False)
            yield ("obs_stderr", False)
            raise RuntimeError("mapping-items-failed")

    logger = create_structured_logger(_FaultyMapping())  # type: ignore[arg-type]
    assert isinstance(logger, StructuredEventLogger)
    assert logger.settings.observability_enabled is True
    assert logger.settings.observability_stderr is False
