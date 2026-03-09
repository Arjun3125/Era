"""Orchestrator plugin for inter-stage contract validation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import Any, Dict, Mapping, Sequence, Tuple

from core.contracts import (
    ContractValidationContract,
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import ContractValidationEngine


def _coerce_iterable_items(value: Any, *, preserve_partial: bool = False) -> list[Any] | None:
    if value is None:
        return None
    items: list[Any] = []
    iterator = iter(value)
    while True:
        try:
            items.append(next(iterator))
        except StopIteration:
            return items
        except Exception:
            if preserve_partial and items:
                return items
            return None


def _coerce_mapping(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        items = _coerce_iterable_items(value.items(), preserve_partial=True)
        if items is None:
            return {}
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items = _coerce_iterable_items(value, preserve_partial=True)
        if raw_items is None:
            return None
        items = []
        for raw_item in raw_items:
            if isinstance(raw_item, Mapping):
                return None
            try:
                key, item_value = raw_item
            except Exception:
                return None
            items.append((key, item_value))
    elif isinstance(value, (str, bytes, bytearray)):
        text = ContractValidationModule._normalize_text(value)
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return None
        return _coerce_mapping(parsed)
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = ContractValidationModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class ContractValidationModule(ModulePlugin):
    """Pipeline module that validates cross-stage contract consistency."""

    engine: ContractValidationEngine

    @classmethod
    def create(cls) -> "ContractValidationModule":
        return cls(engine=ContractValidationEngine())

    def name(self) -> str:
        return "contract_validation"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "validates_contract_dependencies": True,
            "validates_end_to_end_contracts": True,
            "emits_contract_validation_contract": True,
            "supports_degraded_continuation": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context.state, dict):
            raise TypeError("ExecutionContext.state must be a dictionary.")
        if not isinstance(context.config, dict):
            raise TypeError("ExecutionContext.config must be a dictionary.")
        if not isinstance(context.metadata, dict):
            raise TypeError("ExecutionContext.metadata must be a dictionary.")
        if not isinstance(context.input_contract.metadata, dict):
            raise TypeError("InputContract.metadata must be a dictionary.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        sources = self._collect_sources(context)
        try:
            validation_raw = self.engine.validate(state=context.state)
            validation = self._normalize_validation_result(validation_raw)
            contract = validation["contract"]
            issues = self._to_string_list(validation["issues"])
            checks = self._normalize_checks(validation["checks"])
            if contract.error_count > 0:
                status = ModuleStatus.FAILED
            elif contract.warning_count > 0:
                status = ModuleStatus.DEGRADED
            else:
                status = ModuleStatus.SUCCESS

            return ModuleResult(
                status=status,
                outputs={
                    "contract_validation_contract": contract,
                    "contract_validation_issues": issues,
                    "contract_validation_checks": checks,
                    "contract_validation_sources": dict(sources),
                },
                metrics={
                    "contract_validation_warning_count": contract.warning_count,
                    "contract_validation_error_count": contract.error_count,
                    "contract_validation_passed": contract.passed,
                    "contract_validation_check_count": len(checks),
                    "contract_validation_issue_count": len(issues),
                },
                errors=issues,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            message = f"{type(exc).__name__}: {exc}"
            fallback_contract = ContractValidationContract(
                passed=False,
                warning_count=0,
                error_count=1,
                warning_checks=[],
                failed_checks=["contract_validation_engine_exception"],
                checks={"contract_validation_engine_exception": "error"},
                source="contract_validation.module.exception",
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "contract_validation_contract": fallback_contract,
                    "contract_validation_issues": [
                        "contract_validation_engine_exception:error:contract validation engine failed."
                    ],
                    "contract_validation_checks": {"contract_validation_engine_exception": "error"},
                    "contract_validation_sources": dict(sources),
                },
                metrics={
                    "contract_validation_warning_count": 0,
                    "contract_validation_error_count": 1,
                    "contract_validation_passed": False,
                    "contract_validation_check_count": 1,
                    "contract_validation_issue_count": 1,
                },
                errors=[message],
            )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"engine": type(self.engine).__name__})

    @staticmethod
    def _collect_sources(context: ExecutionContext) -> Dict[str, bool]:
        return {
            "request_context_contract": ContractValidationModule._has_normalized_key(
                context.state, ("request_context_contract",)
            ),
            "runtime_config_contract": ContractValidationModule._has_normalized_key(
                context.state, ("runtime_config_contract",)
            ),
            "mode_contract": ContractValidationModule._has_normalized_key(context.state, ("mode_contract",)),
            "domain_analysis_contract": ContractValidationModule._has_normalized_key(
                context.state, ("domain_analysis_contract",)
            ),
            "knowledge_contract": ContractValidationModule._has_normalized_key(
                context.state, ("knowledge_contract",)
            ),
            "council_contract": ContractValidationModule._has_normalized_key(
                context.state, ("council_contract",)
            ),
            "council_normalization_contract": ContractValidationModule._has_normalized_key(
                context.state, ("council_normalization_contract",)
            ),
            "decision_contract": ContractValidationModule._has_normalized_key(
                context.state, ("decision_contract",)
            ),
            "decision_packaging_contract": ContractValidationModule._has_normalized_key(
                context.state, ("decision_packaging_contract",)
            ),
            "decision_package": ContractValidationModule._has_normalized_key(
                context.state, ("decision_package",)
            ),
            "routing_context": ContractValidationModule._has_normalized_key(
                context.state, ("routing_context",)
            ),
        }

    @classmethod
    def _normalize_validation_result(cls, value: Any) -> Dict[str, Any]:
        payload = cls._to_mapping(value)

        checks_raw = cls._read_field(value, payload, "checks")
        checks = cls._normalize_checks(checks_raw)
        issues_raw = cls._read_field(value, payload, "issues")
        issues = cls._to_string_list(issues_raw)

        normalization_warnings: list[str] = []
        if checks_raw not in (None, "", {}) and not cls._is_mapping_like(checks_raw):
            normalization_warnings.append(
                "contract_validation_result_warning:invalid checks payload normalized."
            )
        if issues_raw not in (None, "", []) and not cls._is_string_list_like(issues_raw):
            normalization_warnings.append(
                "contract_validation_result_warning:invalid issues payload normalized."
            )

        contract_raw = cls._read_field(value, payload, "contract")
        if isinstance(contract_raw, ContractValidationContract):
            contract = contract_raw
        else:
            if contract_raw not in (None, "", {}):
                normalization_warnings.append(
                    "contract_validation_result_warning:invalid contract payload rebuilt."
                )
            contract = cls._build_contract(
                checks=checks,
                issues=issues + normalization_warnings,
            )

        if normalization_warnings:
            issues = cls._dedupe_strings(issues + normalization_warnings)
            checks = dict(checks)
            checks.setdefault("contract_validation_result_shape", "warning")

            warning_checks = list(contract.warning_checks)
            if "contract_validation_result_shape" not in warning_checks:
                warning_checks.append("contract_validation_result_shape")
            contract.warning_checks = warning_checks
            contract.warning_count = max(contract.warning_count, 1)
            contract.passed = contract.error_count == 0

        return {
            "contract": contract,
            "issues": issues,
            "checks": checks if checks else dict(contract.checks),
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = ContractValidationModule._normalize_key_name(field)
        for raw_key, raw_value in (_coerce_mapping(payload) or {}).items():
            if ContractValidationModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _normalize_checks(value: Any) -> Dict[str, str]:
        mapping = _coerce_mapping(value)
        if mapping is None:
            return {}
        normalized: Dict[str, str] = {}
        for raw_key, raw_value in mapping.items():
            key = ContractValidationModule._normalize_text(raw_key)
            if not key:
                continue
            status = ContractValidationModule._normalize_text(raw_value).lower()
            if status not in {"pass", "warning", "error"}:
                status = "warning"
            normalized[key] = status
        return normalized

    @staticmethod
    def _build_contract(
        *,
        checks: Mapping[str, str],
        issues: Sequence[str],
    ) -> ContractValidationContract:
        normalized_checks = _coerce_mapping(checks) or {}
        warning_checks = [
            name for name, status in normalized_checks.items() if str(status).strip().lower() == "warning"
        ]
        failed_checks = [
            name for name, status in normalized_checks.items() if str(status).strip().lower() == "error"
        ]
        warning_count = len(warning_checks)
        error_count = len(failed_checks)
        if issues and warning_count == 0 and error_count == 0:
            warning_count = 1
            warning_checks.append("contract_validation_result_issues")
            normalized_checks = dict(normalized_checks)
            normalized_checks["contract_validation_result_issues"] = "warning"

        return ContractValidationContract(
            passed=(error_count == 0),
            warning_count=warning_count,
            error_count=error_count,
            warning_checks=warning_checks,
            failed_checks=failed_checks,
            checks=dict(normalized_checks),
            source="contract_validation.module.normalized_result",
        )

    @staticmethod
    def _to_string_list(value: Any) -> list[str]:
        if value in (None, ""):
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [ContractValidationModule._normalize_text(value)]
        elif isinstance(value, str):
            raw_items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            items = _coerce_iterable_items(value, preserve_partial=True)
            if items is None:
                return []
            raw_items = [ContractValidationModule._normalize_text(item) for item in items]
        elif isinstance(value, Iterable):
            items = _coerce_iterable_items(value, preserve_partial=True)
            if items is None:
                return []
            raw_items = [ContractValidationModule._normalize_text(item) for item in items]
        else:
            return []
        return ContractValidationModule._dedupe_strings(raw_items)

    @staticmethod
    def _dedupe_strings(values: Sequence[str]) -> list[str]:
        deduped: list[str] = []
        seen = set()
        for value in values:
            text = ContractValidationModule._normalize_text(value)
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)
        return deduped

    @staticmethod
    def _has_normalized_key(source: Mapping[str, Any], keys: Tuple[str, ...]) -> bool:
        return ContractValidationModule._read_normalized_key(source, keys) is not None

    @staticmethod
    def _read_normalized_key(source: Mapping[str, Any], keys: Tuple[str, ...]) -> Any:
        if not isinstance(source, Mapping):
            return None
        normalized_keys = {ContractValidationModule._normalize_key_name(key) for key in keys}
        for raw_key, value in (_coerce_mapping(source) or {}).items():
            if ContractValidationModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        return _coerce_mapping(value) or {}

    @staticmethod
    def _is_mapping_like(value: Any) -> bool:
        return _coerce_mapping(value) is not None

    @staticmethod
    def _is_string_list_like(value: Any) -> bool:
        if isinstance(value, (str, bytes, bytearray)):
            return True
        if isinstance(value, Sequence) and not isinstance(value, Mapping):
            return True
        if isinstance(value, Iterable) and not isinstance(value, Mapping):
            return True
        return False

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            ContractValidationModule._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )
