"""Domain analysis engine wrapping persona domain detector."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from core.contracts import DomainAnalysisContract
from persona.domain_detector import analyze_situation

_VALID_STAKES = {"low", "medium", "high"}
_VALID_REVERSIBILITY = {
    "fully_reversible",
    "partially_reversible",
    "irreversible",
}
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


def _coerce_iterable_items(
    value: Iterable[Any],
    *,
    preserve_partial: bool,
) -> tuple[List[Any], bool]:
    collected: List[Any] = []
    iterator = iter(value)
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            return collected, False
        except Exception:
            if preserve_partial:
                return collected, True
            return [], True
        collected.append(item)


def _coerce_mapping(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        try:
            source_items = value.items()
        except Exception:
            return {}
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
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
        key = DomainAnalysisEngine._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class DomainAnalysisResult:
    """Structured domain analysis output."""

    domain_contract: DomainAnalysisContract
    analysis_result: Dict[str, Any]
    warnings: List[str]


@dataclass
class DomainAnalysisEngine:
    """Normalize domain analysis outputs for pipeline stages."""

    llm_adapter: Optional[Any] = None

    def run(self, *, user_input: str) -> DomainAnalysisResult:
        analysis = analyze_situation(user_input, llm_adapter=self.llm_adapter)
        normalized_analysis, warnings = self._normalize_analysis_payload(
            analysis,
            default_problem=user_input,
        )
        contract = self._to_contract(normalized_analysis, source="domain_detector")
        return DomainAnalysisResult(
            domain_contract=contract,
            analysis_result=normalized_analysis,
            warnings=warnings,
        )

    def from_routing_context(self, routing_context: Any) -> DomainAnalysisResult:
        normalized_analysis, warnings = self._normalize_analysis_payload(
            routing_context,
            default_problem="",
        )
        contract = self._to_contract(normalized_analysis, source="routing_context")
        return DomainAnalysisResult(
            domain_contract=contract,
            analysis_result=normalized_analysis,
            warnings=warnings,
        )

    @staticmethod
    def _to_contract(analysis: Mapping[str, Any], *, source: str) -> DomainAnalysisContract:
        domains = DomainAnalysisEngine._normalize_domains(analysis.get("domains"), warnings=[])
        if not domains:
            domains = ["strategy"]

        raw_scores = DomainAnalysisEngine._normalize_domain_scores(
            analysis.get("domain_scores"),
            warnings=[],
        )
        domain_scores: Dict[str, float] = {}
        for domain, score in raw_scores.items():
            try:
                numeric = float(score)
            except Exception:
                continue
            if not math.isfinite(numeric):
                continue
            domain_scores[str(domain).strip().lower()] = max(0.0, min(1.0, numeric))

        confidence = DomainAnalysisEngine._normalize_domain_confidence(
            analysis.get("domain_confidence"),
            fallback=max(domain_scores.values(), default=0.0),
            warnings=[],
        )

        stakes = DomainAnalysisEngine._normalize_stakes(analysis.get("stakes"), warnings=[])
        reversibility = DomainAnalysisEngine._normalize_reversibility(
            analysis.get("reversibility"),
            warnings=[],
        )

        entities = DomainAnalysisEngine._normalize_entities(
            analysis.get("key_entities"),
            warnings=[],
        )

        source_value = DomainAnalysisEngine._normalize_text(source) or "domain_analysis"

        return DomainAnalysisContract(
            domains=domains,
            domain_confidence=float(confidence),
            stakes=stakes,
            reversibility=reversibility,
            key_entities=entities,
            domain_scores=domain_scores,
            source=source_value,
        )

    @staticmethod
    def _normalize_analysis_payload(
        raw: Any,
        *,
        default_problem: str,
    ) -> tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        payload = DomainAnalysisEngine._coerce_payload(raw, warnings)

        problem = DomainAnalysisEngine._normalize_text(
            payload.get("problem", default_problem)
        ) or DomainAnalysisEngine._normalize_text(default_problem)
        domains = DomainAnalysisEngine._normalize_domains(payload.get("domains"), warnings)
        domain_scores = DomainAnalysisEngine._normalize_domain_scores(
            payload.get("domain_scores"),
            warnings,
        )

        if not domains and domain_scores:
            ranked = sorted(domain_scores.items(), key=lambda item: item[1], reverse=True)
            domains = [domain for domain, _ in ranked[:3]]
            warnings.append("domains missing; derived domains from domain_scores.")

        fallback_confidence = max(domain_scores.values(), default=0.0)
        confidence = DomainAnalysisEngine._normalize_domain_confidence(
            payload.get("domain_confidence"),
            fallback=fallback_confidence,
            warnings=warnings,
        )
        stakes = DomainAnalysisEngine._normalize_stakes(payload.get("stakes"), warnings)
        reversibility = DomainAnalysisEngine._normalize_reversibility(
            payload.get("reversibility"),
            warnings,
        )
        key_entities = DomainAnalysisEngine._normalize_entities(
            payload.get("key_entities"),
            warnings,
        )

        normalized: Dict[str, Any] = {
            "problem": problem,
            "domains": domains or ["strategy"],
            "domain_confidence": confidence,
            "stakes": stakes,
            "reversibility": reversibility,
            "key_entities": key_entities,
            "domain_scores": domain_scores,
        }

        for passthrough in ("llm_analysis", "llm_error"):
            if passthrough not in payload:
                continue
            normalized_value = DomainAnalysisEngine._to_jsonable(
                payload.get(passthrough),
                warnings=warnings,
                path=passthrough,
            )
            if normalized_value is None:
                continue
            normalized[passthrough] = normalized_value

        return normalized, DomainAnalysisEngine._dedupe_warnings(warnings)

    @staticmethod
    def _coerce_payload(raw: Any, warnings: List[str]) -> Dict[str, Any]:
        mapping = _coerce_mapping(raw)
        if mapping is not None:
            return mapping
        if raw in (None, ""):
            return {}
        if isinstance(raw, (str, bytes, bytearray)):
            if isinstance(raw, (bytes, bytearray)):
                text = bytes(raw).decode("utf-8", errors="replace").strip()
            else:
                text = raw.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                warnings.append("Invalid analysis payload string ignored.")
                return {}
            parsed_mapping = _coerce_mapping(parsed)
            if parsed_mapping is not None:
                return parsed_mapping
            warnings.append("Non-dict analysis payload JSON ignored.")
            return {}

        warnings.append("Invalid analysis payload ignored.")
        return {}

    @staticmethod
    def _normalize_domains(value: Any, warnings: List[str]) -> List[str]:
        if isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, (bytes, bytearray)):
            raw = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, (list, tuple, set)):
            raw = [DomainAnalysisEngine._normalize_text(item) for item in value]
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [DomainAnalysisEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append("domains iterable iteration failed; partial values preserved.")
        else:
            if value not in (None, ""):
                warnings.append("Invalid domains payload normalized to default.")
            raw = []

        normalized: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(lowered)
        return normalized

    @staticmethod
    def _normalize_domain_scores(
        value: Any,
        warnings: List[str],
    ) -> Dict[str, float]:
        mapping = _coerce_mapping(value)
        if mapping is None:
            if value not in (None, "", {}):
                warnings.append("Invalid domain_scores payload ignored.")
            return {}

        normalized: Dict[str, float] = {}
        for raw_key, raw_score in mapping.items():
            key = DomainAnalysisEngine._normalize_text(raw_key).lower()
            if not key:
                continue
            try:
                score = float(raw_score)
            except Exception:
                warnings.append(f"Invalid domain_scores value for '{key}' ignored.")
                continue
            if not math.isfinite(score):
                warnings.append(f"Non-finite domain_scores value for '{key}' ignored.")
                continue
            if score < 0.0:
                warnings.append(f"Negative domain_scores value for '{key}' clamped to 0.0.")
                score = 0.0
            elif score > 1.0:
                warnings.append(f"domain_scores value for '{key}' above 1.0 clamped to 1.0.")
                score = 1.0
            normalized[key] = score
        return normalized

    @staticmethod
    def _normalize_domain_confidence(
        value: Any,
        *,
        fallback: float,
        warnings: List[str],
    ) -> float:
        fallback_value = max(0.0, min(1.0, float(fallback or 0.0)))
        if value is None:
            return fallback_value
        try:
            score = float(value)
        except Exception:
            warnings.append("Invalid domain_confidence normalized to fallback.")
            return fallback_value
        if not math.isfinite(score):
            warnings.append("Non-finite domain_confidence normalized to fallback.")
            return fallback_value
        if score < 0.0:
            warnings.append("Negative domain_confidence clamped to 0.0.")
            return 0.0
        if score > 1.0:
            warnings.append("domain_confidence above 1.0 clamped to 1.0.")
            return 1.0
        return score

    @staticmethod
    def _normalize_stakes(value: Any, warnings: List[str]) -> str:
        stakes = DomainAnalysisEngine._normalize_text(value).lower().replace("-", "_")
        if not stakes:
            stakes = "medium"
        stakes = _STAKES_ALIASES.get(stakes, stakes)
        if stakes in _VALID_STAKES:
            return stakes
        warnings.append(f"Unsupported stakes '{stakes}' normalized to 'medium'.")
        return "medium"

    @staticmethod
    def _normalize_reversibility(value: Any, warnings: List[str]) -> str:
        if isinstance(value, bool):
            return "fully_reversible" if value else "irreversible"

        reversibility = DomainAnalysisEngine._normalize_text(value).lower().replace("-", "_")
        if not reversibility:
            reversibility = "partially_reversible"
        reversibility = _REVERSIBILITY_ALIASES.get(reversibility, reversibility)
        if reversibility in _VALID_REVERSIBILITY:
            return reversibility
        warnings.append(
            f"Unsupported reversibility '{reversibility}' normalized to 'partially_reversible'."
        )
        return "partially_reversible"

    @staticmethod
    def _normalize_entities(value: Any, warnings: List[str]) -> List[str]:
        if isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, (bytes, bytearray)):
            raw = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, (list, tuple, set)):
            raw = [DomainAnalysisEngine._normalize_text(item) for item in value]
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [DomainAnalysisEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append("key_entities iterable iteration failed; partial values preserved.")
        else:
            if value not in (None, ""):
                warnings.append("Invalid key_entities payload ignored.")
            return []

        entities: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            entities.append(item)
        return entities[:20]

    @staticmethod
    def _to_jsonable(value: Any, *, warnings: List[str], path: str) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if math.isfinite(value):
                return value
            warnings.append(f"{path} had non-finite float and was dropped.")
            return None
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace")
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Mapping):
            result: Dict[str, Any] = {}
            items, failed = _coerce_iterable_items(value.items(), preserve_partial=True)
            if failed:
                warnings.append(f"{path} mapping iteration failed; partial values preserved.")
            for raw_key, raw_item in items:
                item = DomainAnalysisEngine._to_jsonable(
                    raw_item,
                    warnings=warnings,
                    path=f"{path}.{DomainAnalysisEngine._normalize_text(raw_key)}",
                )
                if item is None:
                    continue
                key = DomainAnalysisEngine._normalize_text(raw_key)
                if not key:
                    continue
                result[key] = item
            return result
        if isinstance(value, (list, tuple, set)):
            items: List[Any] = []
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            if failed:
                warnings.append(f"{path} iterable iteration failed; partial values preserved.")
            for index, raw_item in enumerate(raw_items):
                item = DomainAnalysisEngine._to_jsonable(
                    raw_item,
                    warnings=warnings,
                    path=f"{path}[{index}]",
                )
                if item is None:
                    continue
                items.append(item)
            return items

        warnings.append(f"{path} used non-serializable value and was stringified.")
        return str(value)

    @staticmethod
    def _dedupe_warnings(warnings: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            deduped.append(warning)
        return deduped

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()
