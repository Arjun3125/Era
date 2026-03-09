"""Orchestrator plugin for knowledge synthesis stage."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from core.contracts import (
    ExecutionContext,
    KnowledgeContract,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import KnowledgeSynthesisEngine


def _coerce_iterable_items(
    value: Any,
    *,
    preserve_partial: bool,
) -> tuple[list[Any], bool]:
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
            try:
                key, item_value = raw_item
            except Exception:
                return None
            items.append((key, item_value))
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = KnowledgeSynthesisModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class KnowledgeSynthesisModule(ModulePlugin):
    """Pipeline module that retrieves/synthesizes contextual knowledge."""

    engine: KnowledgeSynthesisEngine

    @classmethod
    def create(cls) -> "KnowledgeSynthesisModule":
        return cls(engine=KnowledgeSynthesisEngine())

    def name(self) -> str:
        return "knowledge_synthesis"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "builds_knowledge_contract": True,
            "supports_domain_confidence": True,
            "supports_extra_context": True,
            "normalizes_knowledge_inputs": True,
            "supports_mode_specific_item_limits": True,
            "emits_knowledge_warnings": True,
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
        if not isinstance(context.input_contract.user_input, str):
            raise TypeError("InputContract.user_input must be a string.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        mode = self._resolve_mode(context)
        routing_context, routing_sources = self._merge_routing_context(context)

        try:
            inputs_raw = self.engine.resolve_inputs(mode=mode, routing_context=routing_context)
            inputs = self._normalize_inputs(
                inputs_raw,
                fallback_mode=mode,
                routing_context=routing_context,
            )
            synthesis_raw = self.engine.run(
                user_input=context.input_contract.user_input,
                active_domains=list(inputs["active_domains"]),
                domain_confidence=float(inputs["domain_confidence"]),
                max_items=int(inputs["max_items"]),
                extra_context=list(inputs["extra_context"]),
            )
            synthesis = self._normalize_synthesis_result(
                synthesis_raw,
                fallback_active_domains=list(inputs["active_domains"]),
                fallback_domain_confidence=float(inputs["domain_confidence"]),
                fallback_max_items=int(inputs["max_items"]),
            )
            knowledge_contract = synthesis["knowledge_contract"]
            knowledge_result = synthesis["knowledge_result"]
            warnings = self._dedupe_warnings(
                list(inputs["warnings"]) + list(synthesis["warnings"])
            )
            status = ModuleStatus.SUCCESS if not warnings else ModuleStatus.DEGRADED
            candidate_quality = self._safe_float(
                knowledge_contract.quality.get("candidate_quality"),
                fallback=0.0,
            )
            return ModuleResult(
                status=status,
                outputs={
                    "knowledge_contract": knowledge_contract,
                    "knowledge_result": knowledge_result,
                    "synthesized_knowledge": self._to_string_list(
                        knowledge_result.get("synthesized_knowledge", []) or []
                    ),
                    "knowledge_synthesis_warnings": warnings,
                    "knowledge_synthesis_sources": list(routing_sources),
                },
                metrics={
                    "knowledge_items": len(knowledge_contract.synthesized_items),
                    "domain_count": len(knowledge_contract.active_domains),
                    "candidate_quality": candidate_quality,
                    "knowledge_warning_count": len(warnings),
                    "knowledge_source_count": len(routing_sources),
                },
                errors=warnings,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            empty_contract = KnowledgeContract()
            message = f"{type(exc).__name__}: {exc}"
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "knowledge_contract": empty_contract,
                    "knowledge_result": {"synthesized_knowledge": [], "error": str(exc)},
                    "synthesized_knowledge": [],
                    "knowledge_synthesis_warnings": [message],
                    "knowledge_synthesis_sources": list(routing_sources),
                },
                errors=[message],
            )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"default_max_items": self.engine.default_max_items})

    @staticmethod
    def _resolve_mode(context: ExecutionContext) -> str:
        routing_context = KnowledgeSynthesisModule._read_normalized_key(
            context.state,
            ("routing_context",),
        )
        mode_candidates = (
            KnowledgeSynthesisModule._read_normalized_key(context.state, ("resolved_mode", "mode")),
            KnowledgeSynthesisModule._read_normalized_key(context.state, ("requested_mode", "mode")),
            KnowledgeSynthesisModule._read_normalized_key(context.metadata, ("requested_mode", "mode")),
            KnowledgeSynthesisModule._read_normalized_key(
                context.input_contract.metadata,
                ("requested_mode", "mode"),
            ),
            KnowledgeSynthesisModule._read_normalized_key(context.config, ("requested_mode", "mode")),
            KnowledgeSynthesisModule._read_normalized_key(routing_context, ("requested_mode", "mode"))
            if isinstance(routing_context, Mapping) or _coerce_mapping(routing_context)
            else None,
            "meeting",
        )
        for candidate in mode_candidates:
            text = KnowledgeSynthesisModule._normalize_text(candidate).lower()
            if text:
                return text
        return "meeting"

    @staticmethod
    def _merge_routing_context(context: ExecutionContext) -> Tuple[Dict[str, Any], list[str]]:
        merged: Dict[str, Any] = {}
        sources: list[str] = []
        for source_name, payload in (
            (
                "context.config.routing_context",
                KnowledgeSynthesisModule._read_normalized_key(context.config, ("routing_context",)),
            ),
            (
                "input.metadata.routing_context",
                KnowledgeSynthesisModule._read_normalized_key(
                    context.input_contract.metadata,
                    ("routing_context",),
                ),
            ),
            (
                "run.metadata.routing_context",
                KnowledgeSynthesisModule._read_normalized_key(context.metadata, ("routing_context",)),
            ),
            (
                "state.routing_context",
                KnowledgeSynthesisModule._read_normalized_key(context.state, ("routing_context",)),
            ),
        ):
            payload_mapping = _coerce_mapping(payload)
            if payload_mapping is None:
                continue
            merged.update(payload_mapping)
            sources.append(source_name)

        deduped_sources: list[str] = []
        seen = set()
        for source in sources:
            if source in seen:
                continue
            seen.add(source)
            deduped_sources.append(source)
        return merged, deduped_sources

    @staticmethod
    def _safe_float(value: Any, *, fallback: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return fallback
        return numeric if numeric == numeric and numeric not in (float("inf"), float("-inf")) else fallback

    @staticmethod
    def _dedupe_warnings(warnings: list[str]) -> list[str]:
        deduped: list[str] = []
        seen = set()
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            deduped.append(warning)
        return deduped

    @classmethod
    def _normalize_inputs(
        cls,
        value: Any,
        *,
        fallback_mode: str,
        routing_context: Mapping[str, Any],
    ) -> Dict[str, Any]:
        payload = _coerce_mapping(value) or {}
        warnings = cls._to_string_list(cls._read_field(value, payload, "warnings"))

        active_domains_raw = cls._read_field(value, payload, "active_domains")
        active_domains = cls._to_string_list(active_domains_raw, lowercase=True)
        if not active_domains:
            active_domains = cls._to_string_list(routing_context.get("domains"), lowercase=True)
        if not active_domains:
            active_domains = ["strategy"]
            warnings.append("Knowledge inputs missing active_domains; defaulted to ['strategy'].")

        domain_confidence_raw = cls._read_field(value, payload, "domain_confidence")
        domain_confidence = cls._safe_float(
            domain_confidence_raw,
            fallback=cls._safe_float(routing_context.get("domain_confidence"), fallback=0.75),
        )
        if domain_confidence < 0.0:
            domain_confidence = 0.0
        if domain_confidence > 1.0:
            domain_confidence = 1.0

        max_items_raw = cls._read_field(value, payload, "max_items")
        max_items = cls._safe_int(
            max_items_raw,
            fallback=cls._safe_int(
                routing_context.get("max_items"),
                fallback=cls._default_max_items_for_mode(fallback_mode),
                minimum=1,
            ),
            minimum=1,
        )

        extra_context_raw = cls._read_field(value, payload, "extra_context")
        extra_context = cls._to_string_list(extra_context_raw)

        return {
            "active_domains": active_domains,
            "domain_confidence": domain_confidence,
            "max_items": max_items,
            "extra_context": extra_context,
            "warnings": cls._dedupe_warnings(warnings),
        }

    @classmethod
    def _normalize_synthesis_result(
        cls,
        value: Any,
        *,
        fallback_active_domains: list[str],
        fallback_domain_confidence: float,
        fallback_max_items: int,
    ) -> Dict[str, Any]:
        payload = _coerce_mapping(value) or {}
        warnings = cls._to_string_list(cls._read_field(value, payload, "warnings"))

        knowledge_result_raw = cls._read_field(value, payload, "knowledge_result")
        knowledge_result_mapping = _coerce_mapping(knowledge_result_raw)
        knowledge_result = knowledge_result_mapping or {}
        if knowledge_result_raw not in (None, "", {}) and knowledge_result_mapping is None:
            warnings.append("Knowledge synthesis engine returned invalid knowledge_result; normalized.")

        contract_raw = cls._read_field(value, payload, "knowledge_contract")
        if isinstance(contract_raw, KnowledgeContract):
            knowledge_contract = contract_raw
        else:
            contract_mapping = _coerce_mapping(contract_raw)
            if contract_mapping is None and contract_raw not in (None, "", {}):
                warnings.append("Knowledge synthesis engine returned invalid knowledge_contract; rebuilt.")
            contract_payload = contract_mapping or knowledge_result
            synthesized_items = cls._to_string_list(contract_payload.get("synthesized_knowledge"))
            trace_raw = contract_payload.get("knowledge_trace")
            trace = []
            if isinstance(trace_raw, Sequence) and not isinstance(trace_raw, (str, bytes, bytearray)):
                raw_items, _ = _coerce_iterable_items(trace_raw, preserve_partial=True)
                trace = [_coerce_mapping(item) or {} for item in raw_items if isinstance(item, Mapping)]
            elif isinstance(trace_raw, Iterable) and not isinstance(trace_raw, (str, bytes, bytearray, Mapping)):
                raw_items, _ = _coerce_iterable_items(trace_raw, preserve_partial=True)
                trace = [_coerce_mapping(item) or {} for item in raw_items if isinstance(item, Mapping)]

            quality = _coerce_mapping(contract_payload.get("knowledge_quality", {})) or {}
            knowledge_contract = KnowledgeContract(
                active_domains=list(fallback_active_domains),
                synthesized_items=synthesized_items,
                trace=trace,
                quality=quality,
            )

        if not isinstance(knowledge_result.get("synthesized_knowledge"), Sequence) or isinstance(
            knowledge_result.get("synthesized_knowledge"), (str, bytes, bytearray)
        ):
            knowledge_result["synthesized_knowledge"] = list(knowledge_contract.synthesized_items)
        else:
            knowledge_result["synthesized_knowledge"] = cls._to_string_list(
                knowledge_result.get("synthesized_knowledge")
            )[: max(fallback_max_items, 1)]

        knowledge_result.setdefault("active_domains", list(fallback_active_domains))
        knowledge_result.setdefault("domain_confidence", float(fallback_domain_confidence))
        knowledge_result.setdefault("max_items", int(fallback_max_items))
        knowledge_result.setdefault("knowledge_trace", list(knowledge_contract.trace))
        knowledge_result.setdefault("knowledge_quality", dict(knowledge_contract.quality))

        return {
            "knowledge_contract": knowledge_contract,
            "knowledge_result": knowledge_result,
            "warnings": cls._dedupe_warnings(warnings),
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = KnowledgeSynthesisModule._normalize_key_name(field)
        normalized_payload = _coerce_mapping(payload) or {}
        for raw_key, raw_value in normalized_payload.items():
            if KnowledgeSynthesisModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _default_max_items_for_mode(mode: Any) -> int:
        normalized = KnowledgeSynthesisModule._normalize_text(mode).lower()
        if normalized == "darbar":
            return 12
        if normalized in {"meeting", "war"}:
            return 10
        if normalized in {"quick", "baseline"}:
            return 5
        return 5

    @staticmethod
    def _safe_int(value: Any, *, fallback: int, minimum: int) -> int:
        try:
            numeric = int(value)
        except Exception:
            numeric = fallback
        if numeric < minimum:
            return minimum
        return numeric

    @staticmethod
    def _to_string_list(value: Any, *, lowercase: bool = False) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            raw_items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw = [KnowledgeSynthesisModule._normalize_text(item) for item in raw_items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            raw_items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw = [KnowledgeSynthesisModule._normalize_text(item) for item in raw_items]
        else:
            raw = [KnowledgeSynthesisModule._normalize_text(value)]

        cleaned: list[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            text = item.lower() if lowercase else item
            if text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
        return cleaned

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
            KnowledgeSynthesisModule._normalize_text(value)
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
        normalized_keys = {KnowledgeSynthesisModule._normalize_key_name(item) for item in keys}
        try:
            items = source.items()
        except Exception:
            return None
        raw_items, _ = _coerce_iterable_items(items, preserve_partial=True)
        for raw_key, value in raw_items:
            if KnowledgeSynthesisModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None
