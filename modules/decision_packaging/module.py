"""Orchestrator plugin for final decision packaging."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from core.contracts import (
    DecisionContract,
    DecisionPackagingContract,
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import DecisionPackagingEngine


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
        key = DecisionPackagingModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class DecisionPackagingModule(ModulePlugin):
    """Packages final decision outputs for downstream consumers."""

    engine: DecisionPackagingEngine

    @classmethod
    def create(cls) -> "DecisionPackagingModule":
        return cls(engine=DecisionPackagingEngine())

    def name(self) -> str:
        return "decision_packaging"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "packages_final_decision": True,
            "emits_decision_packaging_contract": True,
            "supports_followup_flags": True,
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
        has_decision_contract = (
            self._read_normalized_key(context.state, ("decision_contract",)) is not None
        )
        has_prime_decision = (
            self._read_normalized_key(context.state, ("prime_decision",)) is not None
        )
        if not has_decision_contract and not has_prime_decision:
            raise ValueError(
                "DecisionPackagingModule requires 'decision_contract' or 'prime_decision' in state."
            )

    def execute(self, context: ExecutionContext) -> ModuleResult:
        decision_contract, decision_source = self._resolve_decision_contract(context)
        prime_decision, prime_source = self._resolve_prime_decision(context)
        council_result, council_source = self._resolve_council_result(context)
        knowledge_result, knowledge_source = self._resolve_knowledge_result(context)
        mode = self._resolve_mode(context, prime_decision=prime_decision)

        try:
            packaged_raw = self.engine.package(
                decision_contract=decision_contract,
                prime_decision=prime_decision,
                council_result=council_result,
                knowledge_result=knowledge_result,
                mode=mode,
            )
            packaged = self._normalize_packaging_result(
                packaged_raw,
                fallback_mode=mode,
            )
            status = ModuleStatus.SUCCESS if not packaged["warnings"] else ModuleStatus.DEGRADED
            return ModuleResult(
                status=status,
                outputs={
                    "decision_package": self._to_mapping(packaged["package"]),
                    "decision_packaging_contract": packaged["contract"],
                    "decision_packaging_sources": {
                        "decision_contract": decision_source,
                        "prime_decision": prime_source,
                        "council_result": council_source,
                        "knowledge_result": knowledge_source,
                        "mode": mode,
                    },
                },
                metrics={
                    "decision_packaging_warning_count": len(packaged["warnings"]),
                    "decision_package_requires_followup": bool(packaged["contract"].requires_followup),
                    "decision_package_knowledge_items": int(packaged["contract"].knowledge_item_count),
                },
                errors=self._to_string_list(packaged["warnings"]),
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            message = f"{type(exc).__name__}: {exc}"
            fallback_mode = str(mode or "meeting").strip().lower() or "meeting"
            fallback_package = {
                "final_outcome": "defer",
                "reason": "decision_packaging_module_error",
                "confidence": 0.0,
                "mode": fallback_mode,
                "recommendation": "defer",
                "council_outcome": "engine_error",
                "red_line_concerns": [],
                "knowledge_items_used": 0,
                "requires_followup": True,
                "source": "decision_packaging.module.exception",
            }
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "decision_package": fallback_package,
                    "decision_packaging_contract": self._fallback_contract(mode=fallback_mode),
                    "decision_packaging_sources": {
                        "decision_contract": decision_source,
                        "prime_decision": prime_source,
                        "council_result": council_source,
                        "knowledge_result": knowledge_source,
                        "mode": mode,
                    },
                },
                metrics={
                    "decision_packaging_warning_count": 1,
                    "decision_package_requires_followup": True,
                    "decision_package_knowledge_items": 0,
                },
                errors=[message],
            )

    @staticmethod
    def _resolve_decision_contract(context: ExecutionContext) -> Tuple[DecisionContract | None, str]:
        candidate = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("decision_contract",),
        )
        if isinstance(candidate, DecisionContract):
            return candidate, "state.decision_contract"
        return None, "none"

    @staticmethod
    def _resolve_prime_decision(context: ExecutionContext) -> Tuple[Any, str]:
        candidate = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("prime_decision",),
        )
        if candidate is not None:
            return candidate, "state.prime_decision"
        return None, "none"

    @staticmethod
    def _resolve_council_result(context: ExecutionContext) -> Tuple[Any, str]:
        normalized = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("council_result_normalized",),
        )
        if normalized is not None:
            return normalized, "state.council_result_normalized"
        raw = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("council_result",),
        )
        if raw is not None:
            return raw, "state.council_result"
        contract = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("council_contract",),
        )
        if contract is not None:
            return contract, "state.council_contract"
        return None, "none"

    @staticmethod
    def _resolve_knowledge_result(context: ExecutionContext) -> Tuple[Any, str]:
        result = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("knowledge_result",),
        )
        if result is not None:
            return result, "state.knowledge_result"
        contract = DecisionPackagingModule._read_normalized_key(
            context.state,
            ("knowledge_contract",),
        )
        if contract is not None:
            return contract, "state.knowledge_contract"
        return None, "none"

    @staticmethod
    def _resolve_mode(context: ExecutionContext, *, prime_decision: Any) -> str:
        prime_payload = _coerce_mapping(prime_decision) or {}
        candidates = (
            DecisionPackagingModule._read_normalized_key(context.state, ("resolved_mode", "mode")),
            DecisionPackagingModule._read_normalized_key(context.state, ("requested_mode", "mode")),
            DecisionPackagingModule._read_normalized_key(context.metadata, ("requested_mode", "mode")),
            DecisionPackagingModule._read_normalized_key(
                context.input_contract.metadata,
                ("requested_mode", "mode"),
            ),
            DecisionPackagingModule._read_normalized_key(context.config, ("requested_mode", "mode")),
            DecisionPackagingModule._read_mapping_field(prime_payload, ("mode",)),
            "meeting",
        )
        for candidate in candidates:
            text = DecisionPackagingModule._normalize_text(candidate).lower()
            if text:
                return text
        return "meeting"

    @staticmethod
    def _fallback_contract(*, mode: str) -> DecisionPackagingContract:
        return DecisionPackagingContract(
            final_outcome="defer",
            mode=mode,
            confidence=0.0,
            recommendation="defer",
            council_outcome="engine_error",
            red_line_count=0,
            knowledge_item_count=0,
            requires_followup=True,
            warning_count=1,
            source="decision_packaging.module.exception",
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True)

    @classmethod
    def _normalize_packaging_result(
        cls,
        value: Any,
        *,
        fallback_mode: Any,
    ) -> Dict[str, Any]:
        payload = cls._to_mapping(value)

        package_raw = cls._read_field(value, payload, "package")
        contract_raw = cls._read_field(value, payload, "contract")
        warnings_raw = cls._read_field(value, payload, "warnings")

        package = cls._to_mapping(package_raw)
        mode = (
            cls._normalize_text(
                cls._read_mapping_field(package, ("mode",), default=fallback_mode or "meeting")
            ).lower()
            or "meeting"
        )
        package["final_outcome"] = (
            cls._normalize_text(
                cls._read_mapping_field(package, ("final_outcome",), default="defer")
            ).lower()
            or "defer"
        )
        package["reason"] = (
            cls._normalize_text(
                cls._read_mapping_field(package, ("reason",), default="decision_reason_unavailable")
            )
            or "decision_reason_unavailable"
        )
        package["confidence"] = cls._safe_confidence(
            cls._read_mapping_field(package, ("confidence",), default=0.0)
        )
        package["mode"] = mode
        package["recommendation"] = (
            cls._normalize_text(
                cls._read_mapping_field(package, ("recommendation",), default="defer")
            ).lower()
            or "defer"
        )
        package["council_outcome"] = (
            cls._normalize_text(
                cls._read_mapping_field(package, ("council_outcome",), default="not_invoked")
            ).lower()
            or "not_invoked"
        )

        red_lines = cls._to_string_list(
            cls._read_mapping_field(package, ("red_line_concerns",)),
            lowercase=True,
        )
        package["red_line_concerns"] = red_lines
        package["knowledge_items_used"] = cls._safe_int(
            cls._read_mapping_field(package, ("knowledge_items_used",), default=0)
        )
        requires_followup = cls._to_bool(
            cls._read_mapping_field(package, ("requires_followup",), default=False)
        )
        package["requires_followup"] = bool(requires_followup)
        package["source"] = (
            cls._normalize_text(cls._read_mapping_field(package, ("source",), default="decision_packaging"))
            or "decision_packaging"
        )

        warnings = cls._to_string_list(warnings_raw)
        contract = contract_raw if isinstance(contract_raw, DecisionPackagingContract) else DecisionPackagingContract(
            final_outcome=str(package.get("final_outcome", "defer") or "defer"),
            mode=mode,
            confidence=package["confidence"],
            recommendation=str(package.get("recommendation", "defer") or "defer"),
            council_outcome=str(package.get("council_outcome", "not_invoked") or "not_invoked"),
            red_line_count=len(red_lines),
            knowledge_item_count=int(package.get("knowledge_items_used", 0) or 0),
            requires_followup=bool(requires_followup),
            warning_count=len(warnings),
            source="decision_packaging",
        )

        return {
            "package": package,
            "contract": contract,
            "warnings": warnings,
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = DecisionPackagingModule._normalize_key_name(field)
        normalized_payload = _coerce_mapping(payload) or {}
        for raw_key, raw_value in normalized_payload.items():
            if DecisionPackagingModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        return _coerce_mapping(value) or {}

    @staticmethod
    def _to_string_list(value: Any, *, lowercase: bool = False) -> list[str]:
        if value in (None, ""):
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [DecisionPackagingModule._normalize_text(value)]
        elif isinstance(value, str):
            raw_items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [DecisionPackagingModule._normalize_text(item) for item in items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [DecisionPackagingModule._normalize_text(item) for item in items]
        else:
            return []
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
    def _safe_confidence(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if not (numeric == numeric) or numeric in (float("inf"), float("-inf")):
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            numeric = int(value)
        except Exception:
            return 0
        return max(numeric, 0)

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = DecisionPackagingModule._normalize_text(value).lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return None

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
            DecisionPackagingModule._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _read_normalized_key(source: Mapping[str, Any], keys: Tuple[str, ...]) -> Any:
        if not isinstance(source, Mapping):
            return None
        normalized_keys = {DecisionPackagingModule._normalize_key_name(key) for key in keys}
        payload = _coerce_mapping(source)
        if payload is None:
            return None
        for raw_key, value in payload.items():
            if DecisionPackagingModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None

    @staticmethod
    def _read_mapping_field(
        source: Any,
        keys: Tuple[str, ...],
        *,
        default: Any = None,
    ) -> Any:
        if not isinstance(source, Mapping):
            return default
        normalized_targets = {
            DecisionPackagingModule._normalize_key_name(key) for key in keys
        }
        payload = _coerce_mapping(source)
        if payload is None:
            return default
        for raw_key, value in payload.items():
            if DecisionPackagingModule._normalize_key_name(raw_key) in normalized_targets:
                return value
        return default
