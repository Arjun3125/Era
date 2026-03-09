"""Orchestrator plugin for input/request context normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from core.contracts import (
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
    RequestContextContract,
)

from .engine import InputNormalizationEngine


_DIRECT_ROUTING_HINT_KEYS = (
    "domains",
    "domain",
    "active_domains",
    "domain_confidence",
    "confidence",
    "stakes",
    "risk",
    "risk_level",
    "reversibility",
    "reversible",
    "key_entities",
    "domain_scores",
    "ablation",
    "use_uncertainty_control",
    "uncertainty_signals",
    "force_domain_analysis",
    "problem",
    "extra_context",
    "synthesized_knowledge",
    "knowledge_quality",
)
_NORMALIZED_DIRECT_HINT_KEYS = {
    key.lower().replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")
    for key in _DIRECT_ROUTING_HINT_KEYS
}


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
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = InputNormalizationModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class InputNormalizationModule(ModulePlugin):
    """Pipeline module that normalizes mode and routing context upfront."""

    engine: InputNormalizationEngine

    @classmethod
    def create(cls) -> "InputNormalizationModule":
        return cls(engine=InputNormalizationEngine())

    def name(self) -> str:
        return "input_normalization"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "normalizes_requested_mode": True,
            "normalizes_routing_context": True,
            "supports_mode_aliases": True,
            "supports_routing_context_aliases": True,
            "supports_routing_context_source_precedence": True,
            "emits_request_context_contract": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context.config, dict):
            raise TypeError("ExecutionContext.config must be a dictionary.")
        if not isinstance(context.metadata, dict):
            raise TypeError("ExecutionContext.metadata must be a dictionary.")
        if not isinstance(context.state, dict):
            raise TypeError("ExecutionContext.state must be a dictionary.")
        if not isinstance(context.input_contract.metadata, dict):
            raise TypeError("InputContract.metadata must be a dictionary.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        routing_context, routing_sources = self._merge_routing_context(context)
        requested_mode = self._resolve_requested_mode(context, routing_context)

        try:
            result_raw = self.engine.normalize(
                requested_mode=requested_mode,
                routing_context=routing_context,
            )
            result = self._normalize_engine_result(
                result_raw,
                fallback_mode=requested_mode,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            message = f"{type(exc).__name__}: {exc}"
            fallback_mode = self._normalize_mode(requested_mode)
            fallback_contract = RequestContextContract(
                requested_mode=fallback_mode,
                routing_context={},
                warning_count=1,
                source="input_normalization.module.exception",
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "requested_mode": fallback_mode,
                    "routing_context": {},
                    "request_context_contract": fallback_contract,
                    "request_context_warnings": [message],
                    "request_context_sources": list(routing_sources),
                },
                metrics={
                    "request_context_warning_count": 1,
                    "request_context_domain_count": 0,
                    "request_context_key_count": 0,
                    "request_context_source_count": len(routing_sources),
                },
                errors=[message],
            )

        status = ModuleStatus.SUCCESS if not result["warnings"] else ModuleStatus.DEGRADED
        normalized_domains = self._to_string_list(
            result["normalized_routing_context"].get("domains"),
            lowercase=True,
        )
        return ModuleResult(
            status=status,
            outputs={
                "requested_mode": result["normalized_mode"],
                "routing_context": dict(result["normalized_routing_context"]),
                "request_context_contract": result["contract"],
                "request_context_warnings": list(result["warnings"]),
                "request_context_sources": list(routing_sources),
            },
            metrics={
                "request_context_warning_count": len(result["warnings"]),
                "request_context_domain_count": len(normalized_domains),
                "request_context_key_count": len(result["normalized_routing_context"]),
                "request_context_source_count": len(routing_sources),
            },
            errors=list(result["warnings"]),
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"default_mode": self.engine.default_mode})

    @staticmethod
    def _resolve_requested_mode(
        context: ExecutionContext,
        routing_context: Mapping[str, Any],
    ) -> Any:
        mode_keys = ("requested_mode", "mode")
        candidates = (
            InputNormalizationModule._read_normalized_key(context.state, mode_keys),
            InputNormalizationModule._read_normalized_key(context.metadata, mode_keys),
            InputNormalizationModule._read_normalized_key(context.input_contract.metadata, mode_keys),
            InputNormalizationModule._read_normalized_key(context.config, mode_keys),
            InputNormalizationModule._read_normalized_key(routing_context, mode_keys)
            if isinstance(routing_context, Mapping)
            else None,
        )
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, str) and not candidate.strip():
                continue
            return candidate
        return "meeting"

    @staticmethod
    def _merge_routing_context(context: ExecutionContext) -> Tuple[Dict[str, Any], List[str]]:
        merged: Dict[str, Any] = {}
        sources: List[str] = []

        routing_context_keys = ("routing_context",)
        routing_sources = (
            (
                "context.config.routing_context",
                InputNormalizationModule._read_normalized_key(context.config, routing_context_keys),
            ),
            (
                "input.metadata.routing_context",
                InputNormalizationModule._read_normalized_key(
                    context.input_contract.metadata,
                    routing_context_keys,
                ),
            ),
            (
                "run.metadata.routing_context",
                InputNormalizationModule._read_normalized_key(context.metadata, routing_context_keys),
            ),
            (
                "state.routing_context",
                InputNormalizationModule._read_normalized_key(context.state, routing_context_keys),
            ),
        )
        for source_name, payload in routing_sources:
            payload_mapping = _coerce_mapping(payload)
            if payload_mapping is None:
                continue
            merged.update(payload_mapping)
            sources.append(source_name)

        direct_sources = (
            ("context.config", context.config),
            ("input.metadata", context.input_contract.metadata),
            ("run.metadata", context.metadata),
            ("state", context.state),
        )
        for source_name, source in direct_sources:
            if not isinstance(source, Mapping):
                continue
            touched = False
            payload = _coerce_mapping(source)
            if payload is None:
                continue
            for raw_key, value in payload.items():
                key_text = InputNormalizationModule._normalize_text(raw_key)
                if not key_text:
                    continue
                normalized_key = InputNormalizationModule._normalize_key_name(key_text)
                if normalized_key not in _NORMALIZED_DIRECT_HINT_KEYS:
                    continue
                merged[key_text] = value
                touched = True
            if touched:
                sources.append(f"{source_name}.direct")

        deduped_sources: List[str] = []
        seen = set()
        for source in sources:
            if source in seen:
                continue
            seen.add(source)
            deduped_sources.append(source)

        return merged, deduped_sources

    @classmethod
    def _normalize_engine_result(
        cls,
        value: Any,
        *,
        fallback_mode: Any,
    ) -> Dict[str, Any]:
        payload = _coerce_mapping(value) or {}
        warnings = cls._to_string_list(cls._read_field(value, payload, "warnings"))

        mode_raw = cls._read_field(value, payload, "normalized_mode")
        mode = cls._normalize_mode(mode_raw if mode_raw not in (None, "") else fallback_mode)

        normalized_routing_raw = cls._read_field(value, payload, "normalized_routing_context")
        normalized_routing_mapping = _coerce_mapping(normalized_routing_raw)
        normalized_routing_context = normalized_routing_mapping or {}
        if normalized_routing_raw not in (None, "", {}) and normalized_routing_mapping is None:
            warnings.append("Input normalization engine returned invalid routing context; normalized to empty mapping.")

        contract_raw = cls._read_field(value, payload, "contract")
        if isinstance(contract_raw, RequestContextContract):
            contract = contract_raw
        else:
            contract_mapping = _coerce_mapping(contract_raw)
            if contract_mapping is None and contract_raw not in (None, "", {}):
                warnings.append("Input normalization engine returned invalid contract; rebuilt from normalized values.")
            contract = cls._contract_from_mapping(
                contract_mapping or {},
                fallback_mode=mode,
                fallback_routing_context=normalized_routing_context,
            )
        contract.warning_count = len(cls._dedupe_strings(warnings))

        return {
            "normalized_mode": mode,
            "normalized_routing_context": normalized_routing_context,
            "contract": contract,
            "warnings": cls._dedupe_strings(warnings),
        }

    @classmethod
    def _contract_from_mapping(
        cls,
        contract_mapping: Mapping[str, Any],
        *,
        fallback_mode: str,
        fallback_routing_context: Mapping[str, Any],
    ) -> RequestContextContract:
        mode_value = cls._read_normalized_key(contract_mapping, ("requested_mode", "mode"))
        normalized_mode = cls._normalize_mode(
            mode_value if mode_value not in (None, "") else fallback_mode
        )

        routing_value = cls._read_normalized_key(contract_mapping, ("routing_context",))
        routing_mapping = _coerce_mapping(routing_value)
        normalized_routing_context = routing_mapping or dict(fallback_routing_context)

        source_value = cls._read_normalized_key(contract_mapping, ("source",))
        source = cls._normalize_text(source_value) or "input_normalization"
        return RequestContextContract(
            requested_mode=normalized_mode,
            routing_context=normalized_routing_context,
            warning_count=0,
            source=source,
        )

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = InputNormalizationModule._normalize_key_name(field)
        normalized_payload = _coerce_mapping(payload) or {}
        for raw_key, raw_value in normalized_payload.items():
            if InputNormalizationModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _normalize_mode(value: Any) -> str:
        text = InputNormalizationModule._normalize_text(value).lower()
        return text or "meeting"

    @staticmethod
    def _to_string_list(value: Any, *, lowercase: bool = False) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            raw_items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [InputNormalizationModule._normalize_text(item) for item in items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [InputNormalizationModule._normalize_text(item) for item in items]
        else:
            raw_items = [InputNormalizationModule._normalize_text(value)]

        normalized: list[str] = []
        seen = set()
        for item in raw_items:
            if not item:
                continue
            text = item.lower() if lowercase else item
            if text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            InputNormalizationModule._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _read_normalized_key(source: Mapping[str, Any], keys: Sequence[str]) -> Any:
        if not isinstance(source, Mapping):
            return None
        normalized_keys = {InputNormalizationModule._normalize_key_name(key) for key in keys}
        payload = _coerce_mapping(source)
        if payload is None:
            return None
        for raw_key, value in payload.items():
            if InputNormalizationModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None
