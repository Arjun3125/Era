"""Orchestrator plugin for Prime final decision execution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from core.contracts import (
    DecisionContract,
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import PrimeDecisionEngine


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
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = PrimeDecisionModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class PrimeDecisionModule(ModulePlugin):
    """Pipeline module that invokes Prime decision finalization."""

    engine: PrimeDecisionEngine

    @classmethod
    def create(cls, *, risk_threshold: float = 0.7, llm_adapter: Any = None) -> "PrimeDecisionModule":
        return cls(engine=PrimeDecisionEngine(risk_threshold=risk_threshold, llm_adapter=llm_adapter))

    def name(self) -> str:
        return "prime_decision"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "final_decision_authority": True,
            "normalizes_council_payloads": True,
            "normalizes_minister_payloads": True,
            "emits_decision_contract": True,
            "emits_prime_warnings": True,
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
        has_council_result_normalized = (
            self._read_normalized_key(context.state, ("council_result_normalized",)) is not None
        )
        has_council_result = self._read_normalized_key(context.state, ("council_result",)) is not None
        has_council_contract = self._read_normalized_key(context.state, ("council_contract",)) is not None
        if not has_council_result_normalized and not has_council_result and not has_council_contract:
            raise ValueError(
                "PrimeDecisionModule requires 'council_result_normalized', "
                "'council_result', or 'council_contract' in context.state."
            )

    def execute(self, context: ExecutionContext) -> ModuleResult:
        mode = self._resolve_mode(context)
        council_input, council_source = self._resolve_council_input(context)
        minister_outputs, minister_source = self._resolve_minister_outputs(context, council_input)

        try:
            evaluation_raw = self.engine.evaluate(
                council_recommendation=council_input,
                minister_outputs=minister_outputs,
                mode=mode,
                context=context.state,
            )
            evaluation = self._normalize_evaluation_result(
                evaluation_raw,
                fallback_mode=mode,
            )
            warnings = self._to_string_list(evaluation["warnings"])
            status = ModuleStatus.SUCCESS if not warnings else ModuleStatus.DEGRADED
            return ModuleResult(
                status=status,
                outputs={
                    "prime_decision": self._to_mapping(evaluation["final_decision"]),
                    "decision_contract": evaluation["decision_contract"],
                    "prime_normalized_council": self._to_mapping(evaluation["normalized_council"]),
                    "prime_normalized_minister_outputs": self._normalize_minister_outputs(
                        evaluation["normalized_minister_outputs"]
                    ),
                    "prime_decision_warnings": warnings,
                    "prime_decision_source": council_source,
                    "prime_minister_source": minister_source,
                },
                metrics={
                    "decision_confidence": float(evaluation["decision_contract"].confidence),
                    "council_outcome": evaluation["normalized_council"].get("outcome"),
                    "prime_warning_count": len(warnings),
                },
                errors=warnings,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            message = f"{type(exc).__name__}: {exc}"
            fallback_mode = str(mode or "meeting").strip().lower() or "meeting"
            fallback_decision = {
                "final_outcome": "defer",
                "reason": "prime_decision_module_error",
                "confidence": 0.0,
                "mode": fallback_mode,
            }
            fallback_contract = DecisionContract(
                decision="defer",
                confidence=0.0,
                rationale="prime_decision_module_error",
                mode=fallback_mode,
                metadata={
                    "source": "prime_decision.module.exception",
                    "council_source": council_source,
                    "minister_source": minister_source,
                },
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "prime_decision": fallback_decision,
                    "decision_contract": fallback_contract,
                    "prime_normalized_council": {},
                    "prime_normalized_minister_outputs": {},
                    "prime_decision_warnings": [message],
                    "prime_decision_source": council_source,
                    "prime_minister_source": minister_source,
                },
                errors=[message],
            )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"risk_threshold": self.engine.risk_threshold})

    @staticmethod
    def _resolve_mode(context: ExecutionContext) -> str:
        council_raw = (
            PrimeDecisionModule._read_normalized_key(context.state, ("council_result_normalized",))
            or PrimeDecisionModule._read_normalized_key(context.state, ("council_result",))
        )
        council_mapping = _coerce_mapping(council_raw)
        candidates = (
            PrimeDecisionModule._read_normalized_key(context.state, ("resolved_mode", "mode")),
            PrimeDecisionModule._read_normalized_key(context.state, ("requested_mode", "mode")),
            PrimeDecisionModule._read_normalized_key(context.metadata, ("requested_mode", "mode")),
            PrimeDecisionModule._read_normalized_key(
                context.input_contract.metadata,
                ("requested_mode", "mode"),
            ),
            PrimeDecisionModule._read_normalized_key(context.config, ("requested_mode", "mode")),
            PrimeDecisionModule._read_normalized_key(council_mapping or {}, ("mode",)),
            "meeting",
        )
        for candidate in candidates:
            text = PrimeDecisionModule._normalize_text(candidate).lower()
            if text:
                return text
        return "meeting"

    @staticmethod
    def _resolve_council_input(context: ExecutionContext) -> Tuple[Any, str]:
        normalized = PrimeDecisionModule._read_normalized_key(
            context.state,
            ("council_result_normalized",),
        )
        if normalized is not None:
            return normalized, "state.council_result_normalized"
        raw = PrimeDecisionModule._read_normalized_key(context.state, ("council_result",))
        if raw is not None:
            return raw, "state.council_result"
        return PrimeDecisionModule._read_normalized_key(
            context.state,
            ("council_contract",),
        ), "state.council_contract"

    @staticmethod
    def _resolve_minister_outputs(
        context: ExecutionContext,
        council_input: Any,
    ) -> Tuple[Any, str]:
        council_mapping = _coerce_mapping(council_input)
        candidates = (
            (
                "state.minister_outputs_normalized",
                PrimeDecisionModule._read_normalized_key(context.state, ("minister_outputs_normalized",)),
            ),
            (
                "state.minister_outputs",
                PrimeDecisionModule._read_normalized_key(context.state, ("minister_outputs",)),
            ),
            (
                "council_input.minister_outputs",
                PrimeDecisionModule._read_normalized_key(council_mapping or {}, ("minister_outputs",)),
            ),
            (
                "council_input.minister_positions",
                PrimeDecisionModule._read_normalized_key(council_mapping or {}, ("minister_positions",)),
            ),
            (
                "council_input.council_positions",
                PrimeDecisionModule._read_normalized_key(council_mapping or {}, ("council_positions",)),
            ),
        )
        for source, value in candidates:
            if value is None:
                continue
            return value, source
        return None, "none"

    @classmethod
    def _normalize_evaluation_result(
        cls,
        value: Any,
        *,
        fallback_mode: Any,
    ) -> Dict[str, Any]:
        payload = cls._to_mapping(value)

        final_decision_raw = cls._read_field(value, payload, "final_decision")
        contract_raw = cls._read_field(value, payload, "decision_contract")
        normalized_council_raw = cls._read_field(value, payload, "normalized_council")
        normalized_ministers_raw = cls._read_field(value, payload, "normalized_minister_outputs")
        warnings_raw = cls._read_field(value, payload, "warnings")

        final_decision = cls._to_mapping(final_decision_raw)
        mode = cls._normalize_text(final_decision.get("mode") or fallback_mode or "meeting").lower() or "meeting"
        final_outcome = (
            cls._normalize_text(final_decision.get("final_outcome", "defer")).lower() or "defer"
        )
        reason = cls._normalize_text(final_decision.get("reason", "")) or "prime_decision_reason_unavailable"
        final_decision["final_outcome"] = final_outcome
        final_decision["reason"] = reason
        final_decision["mode"] = mode
        final_decision["confidence"] = cls._safe_confidence(final_decision.get("confidence", 0.0))

        normalized_council = cls._to_mapping(normalized_council_raw)
        normalized_council.setdefault("outcome", "")
        normalized_council.setdefault("recommendation", "")
        normalized_council.setdefault("mode", mode)

        normalized_minister_outputs = cls._normalize_minister_outputs(normalized_ministers_raw)
        warnings = cls._to_string_list(warnings_raw)

        decision_contract = contract_raw if isinstance(contract_raw, DecisionContract) else DecisionContract(
            decision=final_outcome,
            confidence=final_decision["confidence"],
            rationale=reason,
            mode=mode,
            metadata={
                "source": "prime_decision.module.normalized_result",
                "council_outcome": normalized_council.get("outcome", ""),
                "council_recommendation": normalized_council.get("recommendation", ""),
            },
        )

        return {
            "final_decision": final_decision,
            "decision_contract": decision_contract,
            "normalized_council": normalized_council,
            "normalized_minister_outputs": normalized_minister_outputs,
            "warnings": warnings,
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = PrimeDecisionModule._normalize_key_name(field)
        for raw_key, raw_value in (_coerce_mapping(payload) or {}).items():
            if PrimeDecisionModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        return _coerce_mapping(value) or {}

    @classmethod
    def _normalize_minister_outputs(cls, value: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(value, Mapping):
            source_items = (_coerce_mapping(value) or {}).items()
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            mapping_like = _coerce_mapping(value)
            if mapping_like is not None:
                source_items = mapping_like.items()
            else:
                source_items = {
                    cls._normalize_text(item.get("minister", "")).lower(): item
                    for item in (_coerce_iterable_items(value, preserve_partial=True) or [])
                    if isinstance(item, Mapping) and cls._normalize_text(item.get("minister", ""))
                }.items()
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            seq = _coerce_iterable_items(value, preserve_partial=True)
            if seq is None:
                return {}
            mapping_like = _coerce_mapping(seq)
            if mapping_like is not None:
                source_items = mapping_like.items()
            else:
                source_items = {
                    cls._normalize_text(item.get("minister", "")).lower(): item
                    for item in seq
                    if isinstance(item, Mapping) and cls._normalize_text(item.get("minister", ""))
                }.items()
        else:
            return {}
        normalized: Dict[str, Dict[str, Any]] = {}
        for raw_name, raw_payload in source_items:
            name = cls._normalize_text(raw_name).lower()
            if not name:
                continue
            payload = cls._to_mapping(raw_payload)
            normalized[name] = {
                "stance": cls._normalize_text(payload.get("stance", "neutral")).lower() or "neutral",
                "confidence": cls._safe_confidence(payload.get("confidence", 0.0)),
                "reasoning": cls._normalize_text(payload.get("reasoning", "")),
                "red_line_triggered": bool(
                    cls._normalize_text(payload.get("red_line_triggered", "")).lower()
                    in {"1", "true", "yes", "on"}
                    if not isinstance(payload.get("red_line_triggered"), bool)
                    else payload.get("red_line_triggered")
                ),
            }
        return normalized

    @staticmethod
    def _to_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            items = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            raw_items = _coerce_iterable_items(value, preserve_partial=True)
            if raw_items is None:
                return []
            items = [PrimeDecisionModule._normalize_text(item) for item in raw_items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            raw_items = _coerce_iterable_items(value, preserve_partial=True)
            if raw_items is None:
                return []
            items = [PrimeDecisionModule._normalize_text(item) for item in raw_items]
        else:
            items = [PrimeDecisionModule._normalize_text(value)]
        deduped: list[str] = []
        seen = set()
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            PrimeDecisionModule._normalize_text(value)
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
        normalized_keys = {PrimeDecisionModule._normalize_key_name(key) for key in keys}
        for raw_key, value in (_coerce_mapping(source) or {}).items():
            if PrimeDecisionModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None
