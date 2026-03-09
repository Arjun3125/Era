"""Orchestrator plugin for domain analysis stage."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

from core.contracts import (
    DomainAnalysisContract,
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import DomainAnalysisEngine

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}
_VALID_STAKES = {"low", "medium", "high"}
_VALID_REVERSIBILITY = {"fully_reversible", "partially_reversible", "irreversible"}
_STAKES_ALIASES = {
    "moderate": "medium",
    "med": "medium",
    "critical": "high",
    "severe": "high",
    "low_risk": "low",
    "high_risk": "high",
}
_REVERSIBILITY_ALIASES = {
    "reversible": "fully_reversible",
    "partial": "partially_reversible",
    "partially": "partially_reversible",
    "not_reversible": "irreversible",
    "non_reversible": "irreversible",
    "irreversable": "irreversible",
    "yes": "fully_reversible",
    "no": "irreversible",
}
_DOMAIN_HINT_KEYS = (
    "domains",
    "domain",
    "active_domains",
    "domain_scores",
)
_NORMALIZED_DOMAIN_HINT_KEYS = {
    key.lower().replace("-", "_").replace(".", "_").replace(" ", "_").replace("/", "_")
    for key in _DOMAIN_HINT_KEYS
}


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
        key = DomainAnalysisModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class DomainAnalysisModule(ModulePlugin):
    """Pipeline module that computes domains/stakes/reversibility."""

    engine: DomainAnalysisEngine

    @classmethod
    def create(cls, *, llm_adapter: Any = None) -> "DomainAnalysisModule":
        return cls(engine=DomainAnalysisEngine(llm_adapter=llm_adapter))

    def name(self) -> str:
        return "domain_analysis"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "detects_domains": True,
            "detects_stakes": True,
            "detects_reversibility": True,
            "normalizes_domain_contract_fields": True,
            "supports_routing_context_domain_hints": True,
            "supports_force_domain_analysis_toggle": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context.state, dict):
            raise TypeError("ExecutionContext.state must be a dictionary.")
        if not isinstance(context.config, dict):
            raise TypeError("ExecutionContext.config must be a dictionary.")
        if not isinstance(context.input_contract.user_input, str):
            raise TypeError("InputContract.user_input must be a string.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        routing_context_raw = context.state.get("routing_context", {}) or {}
        routing_context = _coerce_mapping(routing_context_raw) or {}

        force = self._parse_bool(routing_context.get("force_domain_analysis"), default=False)
        prefer_routing = self._parse_bool(
            routing_context.get("use_routing_context_analysis"),
            default=False,
        )
        has_domain_hints = self._has_domain_hints(routing_context)

        try:
            if (has_domain_hints and not force) or (prefer_routing and not force):
                analysis_result_raw = self.engine.from_routing_context(routing_context)
                analysis_source = "routing_context"
            else:
                analysis_result_raw = self.engine.run(user_input=context.input_contract.user_input)
                analysis_source = "domain_detector"

            analysis_result = self._normalize_analysis_result(
                analysis_result_raw,
                fallback_source=analysis_source,
            )
            contract = analysis_result["domain_contract"]
            warnings = self._to_string_list(analysis_result["warnings"])
            status = ModuleStatus.SUCCESS if not warnings else ModuleStatus.DEGRADED
            return ModuleResult(
                status=status,
                outputs={
                    "domain_analysis_contract": contract,
                    "domain_analysis_result": _coerce_mapping(analysis_result["analysis_result"]) or {},
                    "domain_analysis_warnings": warnings,
                    "domain_analysis_source": analysis_source,
                },
                metrics={
                    "domain_count": len(contract.domains),
                    "domain_confidence": float(contract.domain_confidence),
                    "domain_warning_count": len(warnings),
                    "domain_analysis_used_routing_context": int(analysis_source == "routing_context"),
                },
                errors=warnings,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            fallback = DomainAnalysisContract(
                domains=["strategy"],
                domain_confidence=0.0,
                stakes="medium",
                reversibility="partially_reversible",
                source="fallback",
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "domain_analysis_contract": fallback,
                    "domain_analysis_result": {"domains": ["strategy"], "error": str(exc)},
                    "domain_analysis_warnings": [f"{type(exc).__name__}: {exc}"],
                    "domain_analysis_source": "fallback",
                },
                metrics={
                    "domain_count": 1,
                    "domain_confidence": 0.0,
                    "domain_warning_count": 1,
                    "domain_analysis_used_routing_context": 0,
                },
                errors=[f"{type(exc).__name__}: {exc}"],
            )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"llm_adapter": bool(self.engine.llm_adapter)})

    @staticmethod
    def _has_domain_hints(routing_context: Any) -> bool:
        for raw_key, value in (_coerce_mapping(routing_context) or {}).items():
            normalized_key = DomainAnalysisModule._normalize_key_name(raw_key)
            if normalized_key not in _NORMALIZED_DOMAIN_HINT_KEYS:
                continue
            if isinstance(value, str):
                if value.strip():
                    return True
                continue
            if isinstance(value, Mapping):
                if _coerce_mapping(value):
                    return True
                continue
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
                items = _coerce_iterable_items(value, preserve_partial=True)
                if items:
                    return True
                continue
            if value is not None:
                return True
        return False

    @staticmethod
    def _parse_bool(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return default
        normalized = DomainAnalysisModule._normalize_text(value).lower()
        if normalized in _TRUTHY:
            return True
        if normalized in _FALSY:
            return False
        return default

    @classmethod
    def _normalize_analysis_result(
        cls,
        value: Any,
        *,
        fallback_source: str,
    ) -> Dict[str, Any]:
        payload = _coerce_mapping(value) or {}
        warnings = cls._to_string_list(cls._read_field(value, payload, "warnings"))

        analysis_raw = cls._read_field(value, payload, "analysis_result")
        analysis_mapping = _coerce_mapping(analysis_raw)
        analysis = analysis_mapping or {}
        if analysis_raw not in (None, "", {}) and analysis_mapping is None:
            warnings.append("Domain analysis engine returned invalid analysis_result; normalized to empty mapping.")

        contract_raw = cls._read_field(value, payload, "domain_contract")
        if isinstance(contract_raw, DomainAnalysisContract):
            contract = contract_raw
        else:
            contract_mapping = _coerce_mapping(contract_raw)
            if contract_mapping is None and contract_raw not in (None, "", {}):
                warnings.append("Domain analysis engine returned invalid domain_contract; rebuilt from analysis_result.")
            contract = cls._contract_from_analysis(
                contract_mapping or analysis,
                fallback_source=fallback_source,
            )

        if not analysis:
            analysis = cls._analysis_from_contract(contract)

        return {
            "domain_contract": contract,
            "analysis_result": analysis,
            "warnings": cls._dedupe_strings(warnings),
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = DomainAnalysisModule._normalize_key_name(field)
        for raw_key, raw_value in (_coerce_mapping(payload) or {}).items():
            if DomainAnalysisModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @staticmethod
    def _analysis_from_contract(contract: DomainAnalysisContract) -> Dict[str, Any]:
        return {
            "domains": list(contract.domains),
            "domain_confidence": float(contract.domain_confidence),
            "stakes": contract.stakes,
            "reversibility": contract.reversibility,
            "key_entities": list(contract.key_entities),
            "domain_scores": dict(contract.domain_scores),
            "source": contract.source,
        }

    @staticmethod
    def _contract_from_analysis(
        analysis: Mapping[str, Any],
        *,
        fallback_source: str,
    ) -> DomainAnalysisContract:
        domains = DomainAnalysisModule._to_string_list(analysis.get("domains"), lowercase=True)
        if not domains:
            domains = ["strategy"]

        domain_confidence = DomainAnalysisModule._safe_float(
            analysis.get("domain_confidence"),
            fallback=0.0,
        )
        domain_confidence = max(0.0, min(domain_confidence, 1.0))

        stakes = (
            DomainAnalysisModule._normalize_text(analysis.get("stakes"))
            .lower()
            .replace("-", "_")
            or "medium"
        )
        stakes = _STAKES_ALIASES.get(stakes, stakes)
        if stakes not in _VALID_STAKES:
            stakes = "medium"

        reversibility = (
            DomainAnalysisModule._normalize_text(analysis.get("reversibility"))
            .lower()
            .replace("-", "_")
            or "partially_reversible"
        )
        reversibility = _REVERSIBILITY_ALIASES.get(reversibility, reversibility)
        if reversibility not in _VALID_REVERSIBILITY:
            reversibility = "partially_reversible"

        raw_scores = analysis.get("domain_scores")
        domain_scores: Dict[str, float] = {}
        normalized_scores = _coerce_mapping(raw_scores)
        if normalized_scores is not None:
            for raw_key, raw_value in normalized_scores.items():
                key = DomainAnalysisModule._normalize_text(raw_key).lower()
                if not key:
                    continue
                score = DomainAnalysisModule._safe_float(raw_value, fallback=None)
                if score is None:
                    continue
                domain_scores[key] = max(0.0, min(score, 1.0))

        entities = DomainAnalysisModule._to_string_list(analysis.get("key_entities"))
        source = (
            DomainAnalysisModule._normalize_text(analysis.get("source", fallback_source))
            or fallback_source
        )

        return DomainAnalysisContract(
            domains=domains,
            domain_confidence=domain_confidence,
            stakes=stakes,
            reversibility=reversibility,
            key_entities=entities,
            domain_scores=domain_scores,
            source=source,
        )

    @staticmethod
    def _to_string_list(value: Any, *, lowercase: bool = False) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            raw_items = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            items = _coerce_iterable_items(value, preserve_partial=True)
            if items is None:
                return []
            raw_items = [DomainAnalysisModule._normalize_text(item) for item in items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            items = _coerce_iterable_items(value, preserve_partial=True)
            if items is None:
                return []
            raw_items = [DomainAnalysisModule._normalize_text(item) for item in items]
        else:
            raw_items = [DomainAnalysisModule._normalize_text(value)]

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
    def _safe_float(value: Any, *, fallback: float | None) -> float | None:
        if value is None:
            return fallback
        try:
            numeric = float(value)
        except Exception:
            return fallback
        if not (numeric == numeric) or numeric in (float("inf"), float("-inf")):
            return fallback
        return numeric

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
            DomainAnalysisModule._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )
