"""Orchestrator plugin that resolves runtime settings for a pipeline run."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import Any, Dict, Mapping, Sequence

from config import canonicalize_runtime_key
from core.contracts import (
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
    RuntimeConfigContract,
)

from .engine import RuntimeConfigEngine


def _coerce_iterable_items(value: Any, *, preserve_partial: bool) -> tuple[list[Any], bool]:
    try:
        iterator = iter(value)
    except Exception:
        return [], True
    items: list[Any] = []
    failed = False
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            break
        except Exception:
            failed = True
            break
        items.append(item)
    if failed and not preserve_partial:
        return [], True
    return items, failed


@dataclass
class RuntimeConfigModule(ModulePlugin):
    """Pipeline module that provides normalized runtime configuration contracts."""

    engine: RuntimeConfigEngine

    @classmethod
    def create(cls) -> "RuntimeConfigModule":
        return cls(engine=RuntimeConfigEngine())

    def name(self) -> str:
        return "runtime_config"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "loads_runtime_settings": True,
            "supports_runtime_overrides": True,
            "supports_runtime_override_aliases": True,
            "enforces_runtime_invariants": True,
            "emits_runtime_config_contract": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context.state, dict):
            raise TypeError("ExecutionContext.state must be a dictionary.")
        if not isinstance(context.config, dict):
            raise TypeError("ExecutionContext.config must be a dictionary.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        try:
            result_raw = self.engine.resolve(
                context_config=context.config,
                metadata=context.metadata,
                input_metadata=context.input_contract.metadata,
            )
            result = self._normalize_resolution_result(result_raw)
        except Exception as exc:  # pragma: no cover - defensive branch
            message = f"{type(exc).__name__}: {exc}"
            contract = RuntimeConfigContract(
                source="runtime_config.module.exception",
                overrides_applied=[],
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "runtime_settings": {},
                    "runtime_config_contract": contract,
                    "runtime_config_warnings": [message],
                },
                metrics={
                    "runtime_overrides_applied": 0,
                    "runtime_warnings": 1,
                },
                errors=[message],
            )

        status = ModuleStatus.SUCCESS if not result["warnings"] else ModuleStatus.DEGRADED
        return ModuleResult(
            status=status,
            outputs={
                "runtime_settings": dict(result["settings_dict"]),
                "runtime_config_contract": result["contract"],
                "runtime_config_warnings": list(result["warnings"]),
            },
            metrics={
                "runtime_overrides_applied": len(result["contract"].overrides_applied),
                "runtime_warnings": len(result["warnings"]),
            },
            errors=list(result["warnings"]),
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True)

    @classmethod
    def _normalize_resolution_result(cls, value: Any) -> Dict[str, Any]:
        payload = cls._coerce_mapping(value) or {}

        warnings = cls._to_string_list(cls._read_field(value, payload, "warnings"))

        settings_raw = cls._read_field(value, payload, "settings_dict")
        settings_mapping = cls._coerce_mapping(settings_raw)
        settings_dict = settings_mapping or {}
        if settings_raw not in (None, "", {}) and settings_mapping is None:
            warnings.append("Runtime config engine returned invalid settings_dict; normalized to empty mapping.")

        contract_raw = cls._read_field(value, payload, "contract")
        if isinstance(contract_raw, RuntimeConfigContract):
            contract = contract_raw
        else:
            contract_mapping = cls._coerce_mapping(contract_raw)
            if contract_mapping is None and contract_raw not in (None, "", {}):
                warnings.append("Runtime config engine returned invalid contract; rebuilt from settings.")
            contract = cls._contract_from_mapping(contract_mapping or settings_dict)

        if not settings_dict:
            settings_dict = cls._settings_from_contract(contract)

        return {
            "settings_dict": settings_dict,
            "contract": contract,
            "warnings": cls._dedupe_strings(warnings),
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = RuntimeConfigModule._normalize_field_name(field)
        normalized_payload = RuntimeConfigModule._coerce_mapping(payload) or {}
        for raw_key, raw_value in normalized_payload.items():
            if RuntimeConfigModule._normalize_field_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _coerce_mapping(value: Any) -> Dict[str, Any] | None:
        if isinstance(value, Mapping):
            try:
                raw_items = value.items()
            except Exception:
                return {}
            items, _ = _coerce_iterable_items(raw_items, preserve_partial=True)
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            if failed and not raw_items:
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
            text = RuntimeConfigModule._normalize_text(value)
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                return None
            return RuntimeConfigModule._coerce_mapping(parsed)
        else:
            return None

        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in items:
            key = RuntimeConfigModule._normalize_text(raw_key)
            if not key or key in normalized:
                continue
            normalized[key] = raw_value
        return normalized

    @staticmethod
    def _settings_from_contract(contract: RuntimeConfigContract) -> Dict[str, Any]:
        return {
            "app_name": contract.app_name,
            "environment": contract.environment,
            "orchestrator_strict": contract.orchestrator_strict,
            "decision_pipeline_enabled": contract.decision_pipeline_enabled,
            "observability_enabled": contract.observability_enabled,
            "observability_emit_events": contract.observability_emit_events,
            "observability_emit_summary": contract.observability_emit_summary,
            "observability_write_file": contract.observability_write_file,
            "observability_stderr": contract.observability_stderr,
            "observability_file": contract.observability_file,
            "overrides_applied": list(contract.overrides_applied),
            "source": contract.source,
        }

    @staticmethod
    def _contract_from_mapping(settings: Mapping[str, Any]) -> RuntimeConfigContract:
        normalized_settings = RuntimeConfigModule._normalize_settings_mapping(settings)
        return RuntimeConfigContract(
            app_name=RuntimeConfigModule._normalize_text(
                normalized_settings.get("app_name"),
                default="era",
            ),
            environment=RuntimeConfigModule._normalize_text(
                normalized_settings.get("environment"),
                default="development",
            ),
            orchestrator_strict=normalized_settings.get("orchestrator_strict", False),
            decision_pipeline_enabled=normalized_settings.get("decision_pipeline_enabled", True),
            observability_enabled=normalized_settings.get("observability_enabled", True),
            observability_emit_events=normalized_settings.get("observability_emit_events", False),
            observability_emit_summary=normalized_settings.get("observability_emit_summary", True),
            observability_write_file=normalized_settings.get("observability_write_file", False),
            observability_stderr=normalized_settings.get("observability_stderr", False),
            observability_file=RuntimeConfigModule._normalize_text(
                normalized_settings.get("observability_file"),
                default="logs/orchestration_events.jsonl",
            ),
            source=RuntimeConfigModule._normalize_text(
                normalized_settings.get("source"),
                default="environment",
            ),
            overrides_applied=RuntimeConfigModule._to_string_list(
                normalized_settings.get("overrides_applied")
            ),
        )

    @staticmethod
    def _normalize_settings_mapping(settings: Mapping[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in (RuntimeConfigModule._coerce_mapping(settings) or {}).items():
            text_key = RuntimeConfigModule._normalize_text(raw_key)
            if not text_key:
                continue
            normalized_key = RuntimeConfigModule._normalize_field_name(text_key)
            if normalized_key and normalized_key not in normalized:
                normalized[normalized_key] = raw_value
            canonical = canonicalize_runtime_key(text_key)
            if canonical and canonical not in normalized:
                normalized[canonical] = raw_value
        return normalized

    @staticmethod
    def _to_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
            raw_items = [text]
        elif isinstance(value, str):
            raw_items = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [str(item).strip() for item in items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [str(item).strip() for item in items]
        else:
            raw_items = [str(value).strip()]
        deduped: list[str] = []
        seen = set()
        for item in raw_items:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    @staticmethod
    def _dedupe_strings(values: Sequence[str]) -> list[str]:
        deduped: list[str] = []
        seen = set()
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)
        return deduped

    @staticmethod
    def _normalize_field_name(value: Any) -> str:
        text = RuntimeConfigModule._normalize_text(value)
        return (
            text.lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _normalize_text(value: Any, *, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
        else:
            text = str(value).strip()
        return text or default
