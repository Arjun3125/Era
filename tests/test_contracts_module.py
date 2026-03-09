"""Tests for module contract normalization."""

from __future__ import annotations

import pytest

from core.contracts.module import ModuleHealth, ModuleResult, ModuleStatus


def test_module_status_coerce_and_validation():
    assert ModuleStatus.coerce("success") == ModuleStatus.SUCCESS
    assert ModuleStatus.coerce("ok") == ModuleStatus.SUCCESS
    assert ModuleStatus.coerce("warn") == ModuleStatus.DEGRADED
    assert ModuleStatus.coerce(ModuleStatus.DEGRADED) == ModuleStatus.DEGRADED
    assert ModuleStatus.coerce(b"failed") == ModuleStatus.FAILED
    with pytest.raises(ValueError, match="Unsupported module status"):
        ModuleStatus.coerce("unknown")


def test_module_health_normalizes_fields():
    health = ModuleHealth(ok=1, details=None)  # type: ignore[arg-type]
    assert health.ok is True
    assert health.details == {}

    health2 = ModuleHealth(ok=False, details={"x": 1})
    assert health2.details == {"x": 1}

    health3 = ModuleHealth(ok="false", details={1: "a"})  # type: ignore[arg-type]
    assert health3.ok is False
    assert health3.details == {"1": "a"}

    health4 = ModuleHealth(ok=True, details=[(b"k", 1), ("k", 2)])  # type: ignore[arg-type]
    assert health4.details == {"k": 1}


def test_module_result_normalizes_status_payloads_and_errors():
    result = ModuleResult(
        status="degraded",  # type: ignore[arg-type]
        outputs=None,  # type: ignore[arg-type]
        metrics=None,  # type: ignore[arg-type]
        errors=[" x ", "x", "", 1],
    )

    assert result.status == ModuleStatus.DEGRADED
    assert result.outputs == {}
    assert result.metrics == {}
    assert result.errors == ["x", "1"]


def test_module_result_coerces_non_sequence_error_to_string():
    result = ModuleResult(
        status=ModuleStatus.SUCCESS,
        errors=RuntimeError("boom"),  # type: ignore[arg-type]
    )
    assert result.errors == ["boom"]


def test_module_result_stringifies_mapping_keys_and_normalizes_iterable_errors():
    result = ModuleResult(
        status="success",  # type: ignore[arg-type]
        outputs={1: "a"},
        metrics={2: 3},
        errors=(item for item in [b" boom ", {"message": "mapped"}, "", "boom"]),
    )

    assert result.outputs == {"1": "a"}
    assert result.metrics == {"2": 3}
    assert result.errors == ["boom", "mapped"]


def test_module_result_accepts_iterable_key_value_outputs_and_metrics():
    result = ModuleResult(
        status=ModuleStatus.SUCCESS,
        outputs=[(b"o", 1), ("o", 2)],  # type: ignore[arg-type]
        metrics=[("m", 3), ("m", 4)],  # type: ignore[arg-type]
    )

    assert result.outputs == {"o": 1}
    assert result.metrics == {"m": 3}


def test_module_result_coerces_mapping_error_payload():
    result = ModuleResult(
        status=ModuleStatus.SUCCESS,
        errors={"error": "failed"},  # type: ignore[arg-type]
    )
    assert result.errors == ["failed"]

    result2 = ModuleResult(
        status=ModuleStatus.SUCCESS,
        errors={"error-message": "mapped failed"},  # type: ignore[arg-type]
    )
    assert result2.errors == ["mapped failed"]


def test_module_health_drops_malformed_iterable_mapping_details():
    health = ModuleHealth(
        ok=True,
        details=[("a", 1), ("bad", 2, 3)],  # type: ignore[arg-type]
    )
    assert health.details == {}


def test_module_result_error_normalization_keeps_partial_items_from_faulty_iterable():
    class _FaultyErrors:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return b" boom "
            if index == 1:
                return {"message": "mapped"}
            raise RuntimeError("boom")

    result = ModuleResult(
        status=ModuleStatus.SUCCESS,
        errors=_FaultyErrors(),  # type: ignore[arg-type]
    )
    assert result.errors == ["boom", "mapped"]
