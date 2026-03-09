"""Input/request context normalization engine for the decision pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from collections.abc import Iterable
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping

from core.contracts import RequestContextContract


_VALID_MODES = {"quick", "meeting", "war", "darbar"}
_VALID_STAKES = {"low", "medium", "high"}
_VALID_REVERSIBILITY = {
    "fully_reversible",
    "partially_reversible",
    "irreversible",
}
_MODE_ALIASES = {
    "fast": "quick",
    "quick_mode": "quick",
    "quickmode": "quick",
    "normal": "meeting",
    "standard": "meeting",
    "default": "meeting",
    "crisis": "war",
    "emergency": "war",
    "board": "darbar",
}
_ROUTING_KEY_ALIASES = {
    "domain": "domains",
    "active_domains": "domains",
    "domain_list": "domains",
    "domain_confidence_score": "domain_confidence",
    "confidence": "domain_confidence",
    "risk": "stakes",
    "risk_level": "stakes",
    "impact": "stakes",
    "reversible": "reversibility",
    "reversable": "reversibility",
}
_STAKES_ALIASES = {
    "moderate": "medium",
    "med": "medium",
    "low_risk": "low",
    "high_risk": "high",
    "critical": "high",
    "severe": "high",
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
_NORMALIZED_ROUTING_KEYS = {
    "domains",
    "domain_confidence",
    "stakes",
    "reversibility",
    "domain_scores",
    "key_entities",
    "synthesized_knowledge",
    "knowledge_quality",
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
        key = InputNormalizationEngine._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class InputNormalizationResult:
    """Normalized request context payload."""

    contract: RequestContextContract
    warnings: List[str]
    normalized_mode: str
    normalized_routing_context: Dict[str, Any]


@dataclass
class InputNormalizationEngine:
    """Normalizes request mode and routing context for deterministic pipelines."""

    default_mode: str = "meeting"

    def normalize(
        self,
        *,
        requested_mode: Any,
        routing_context: Mapping[str, Any] | None,
    ) -> InputNormalizationResult:
        warnings: List[str] = []
        mode = self._normalize_mode(requested_mode, warnings)
        raw_routing_context = routing_context if routing_context is not None else {}
        context = self._normalize_routing_context(raw_routing_context, warnings)
        warnings = self._dedupe_warnings(warnings)

        contract = RequestContextContract(
            requested_mode=mode,
            routing_context=context,
            warning_count=len(warnings),
            source="input_normalization",
        )
        return InputNormalizationResult(
            contract=contract,
            warnings=warnings,
            normalized_mode=mode,
            normalized_routing_context=context,
        )

    def _normalize_mode(self, requested_mode: Any, warnings: List[str]) -> str:
        raw_mode = self.default_mode if requested_mode is None else requested_mode
        mode = self._normalize_text(raw_mode).lower()
        if not mode:
            mode = self._normalize_text(self.default_mode).lower() or "meeting"
        mode = _MODE_ALIASES.get(mode, mode)
        if mode in _VALID_MODES:
            return mode
        fallback = self._normalize_text(self.default_mode).lower() or "meeting"
        warnings.append(f"Unsupported mode '{mode}' normalized to '{fallback}'.")
        return fallback

    def _normalize_routing_context(
        self,
        routing_context: Mapping[str, Any] | Any,
        warnings: List[str],
    ) -> Dict[str, Any]:
        raw_context = self._coerce_routing_context(routing_context, warnings)
        context: Dict[str, Any] = {}
        raw_items, failed = _coerce_iterable_items(raw_context.items(), preserve_partial=True)
        if failed:
            warnings.append("routing_context mapping iteration failed; partial values preserved.")
        for raw_key, raw_value in raw_items:
            key = self._canonicalize_routing_key(raw_key)
            normalized_raw_key = self._normalize_text(raw_key)
            if key in context and key != normalized_raw_key:
                warnings.append(
                    f"Routing key alias '{raw_key}' merged into canonical key '{key}'."
                )
            context[key] = raw_value

        domains = context.get("domains", [])
        normalized_domains = self._normalize_domains(domains, warnings)
        if normalized_domains:
            context["domains"] = normalized_domains
        else:
            context.pop("domains", None)

        if "domain_confidence" in context:
            normalized_confidence = self._normalize_domain_confidence(
                context.get("domain_confidence"),
                warnings,
            )
            if normalized_confidence is None:
                context.pop("domain_confidence", None)
            else:
                context["domain_confidence"] = normalized_confidence

        if "stakes" in context:
            stakes = str(context.get("stakes", "medium")).strip().lower().replace("-", "_")
            stakes = _STAKES_ALIASES.get(stakes, stakes)
            if stakes not in _VALID_STAKES:
                warnings.append(f"Unsupported stakes '{stakes}' normalized to 'medium'.")
                stakes = "medium"
            context["stakes"] = stakes

        if "reversibility" in context:
            reversibility_raw = context.get("reversibility", "partially_reversible")
            reversibility = self._normalize_reversibility(reversibility_raw, warnings)
            if reversibility is None:
                context.pop("reversibility", None)
            else:
                context["reversibility"] = reversibility

        if "key_entities" in context:
            entities = self._normalize_str_list(
                context.get("key_entities"),
                warnings=warnings,
                field_name="key_entities",
            )
            if entities:
                context["key_entities"] = entities
            else:
                context.pop("key_entities", None)

        if "domain_scores" in context:
            normalized_scores = self._normalize_domain_scores(
                context.get("domain_scores"),
                warnings,
            )
            if normalized_scores:
                context["domain_scores"] = normalized_scores
            else:
                context.pop("domain_scores", None)

        context = self._sanitize_context(context, warnings)

        for key in list(context.keys()):
            if context[key] is None:
                context.pop(key, None)

        return context

    @staticmethod
    def _normalize_domains(domains: Any, warnings: List[str]) -> List[str]:
        if isinstance(domains, str):
            raw = [part.strip() for part in domains.split(",")]
        elif isinstance(domains, (bytes, bytearray)):
            raw = [bytes(domains).decode("utf-8", errors="replace").strip()]
        elif isinstance(domains, (list, tuple, set)):
            raw = [InputNormalizationEngine._normalize_text(item) for item in domains]
        elif isinstance(domains, Iterable) and not isinstance(domains, Mapping):
            raw_items, failed = _coerce_iterable_items(domains, preserve_partial=True)
            raw = [InputNormalizationEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append("domains iterable iteration failed; partial values preserved.")
        else:
            if domains not in (None, ""):
                warnings.append("Invalid domains payload ignored during normalization.")
            return []

        cleaned: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            value = item.lower()
            if value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        return cleaned

    @staticmethod
    def _normalize_str_list(
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
    ) -> List[str]:
        if isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, (bytes, bytearray)):
            raw = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, (list, tuple, set)):
            raw = [InputNormalizationEngine._normalize_text(item) for item in value]
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [InputNormalizationEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    f"{field_name} iterable iteration failed; partial values preserved."
                )
        else:
            if value not in (None, ""):
                warnings.append(f"Invalid {field_name} payload ignored during normalization.")
            return []

        cleaned: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            if item in seen:
                continue
            seen.add(item)
            cleaned.append(item)
        return cleaned

    @staticmethod
    def _normalize_domain_confidence(value: Any, warnings: List[str]) -> float | None:
        if value is None:
            return None
        try:
            score = float(value)
        except Exception:
            warnings.append("Invalid domain_confidence normalized to 0.0.")
            return 0.0

        if not math.isfinite(score):
            warnings.append("Non-finite domain_confidence normalized to 0.0.")
            return 0.0

        if score < 0.0:
            warnings.append("Negative domain_confidence clamped to 0.0.")
            return 0.0
        if score > 1.0:
            warnings.append("domain_confidence above 1.0 clamped to 1.0.")
            return 1.0
        return score

    @staticmethod
    def _normalize_domain_scores(
        value: Any,
        warnings: List[str],
    ) -> Dict[str, float]:
        mapping = _coerce_mapping(value)
        if mapping is None:
            if value not in (None, "", {}):
                warnings.append("Invalid domain_scores payload ignored during normalization.")
            return {}

        normalized: Dict[str, float] = {}
        for key, raw_score in mapping.items():
            name = InputNormalizationEngine._normalize_text(key).lower()
            if not name:
                continue
            try:
                score = float(raw_score)
            except Exception:
                warnings.append(f"Invalid domain_scores value for '{name}' ignored.")
                continue

            if not math.isfinite(score):
                warnings.append(f"Non-finite domain_scores value for '{name}' ignored.")
                continue

            if score < 0.0:
                warnings.append(f"Negative domain_scores value for '{name}' clamped to 0.0.")
                score = 0.0
            elif score > 1.0:
                warnings.append(f"domain_scores value for '{name}' above 1.0 clamped to 1.0.")
                score = 1.0

            normalized[name] = score
        return normalized

    @staticmethod
    def _coerce_routing_context(
        value: Any,
        warnings: List[str],
    ) -> Dict[str, Any]:
        mapping = _coerce_mapping(value)
        if mapping is not None:
            return mapping
        if value in (None, ""):
            return {}
        if isinstance(value, (str, bytes, bytearray)):
            if isinstance(value, (bytes, bytearray)):
                text = bytes(value).decode("utf-8", errors="replace").strip()
            else:
                text = value.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                warnings.append("Invalid routing_context string ignored during normalization.")
                return {}
            parsed_mapping = _coerce_mapping(parsed)
            if parsed_mapping is not None:
                return parsed_mapping
            warnings.append("Non-dict routing_context JSON ignored during normalization.")
            return {}
        warnings.append("Invalid routing_context payload ignored during normalization.")
        return {}

    @staticmethod
    def _normalize_reversibility(value: Any, warnings: List[str]) -> str | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return "fully_reversible" if value else "irreversible"

        raw = InputNormalizationEngine._normalize_text(value).lower().replace("-", "_")
        if not raw:
            return None
        raw = _REVERSIBILITY_ALIASES.get(raw, raw)
        if raw in _VALID_REVERSIBILITY:
            return raw
        warnings.append(
            f"Unsupported reversibility '{raw}' normalized to 'partially_reversible'."
        )
        return "partially_reversible"

    def _sanitize_context(
        self,
        context: Mapping[str, Any],
        warnings: List[str],
    ) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        items, failed = _coerce_iterable_items(context.items(), preserve_partial=True)
        if failed:
            warnings.append("routing_context sanitization iteration failed; partial values preserved.")
        for key, value in items:
            normalized_value = self._to_jsonable(
                value,
                warnings=warnings,
                path=f"routing_context.{key}",
            )
            if normalized_value is None:
                continue
            sanitized[key] = normalized_value
        return sanitized

    def _to_jsonable(
        self,
        value: Any,
        *,
        warnings: List[str],
        path: str,
    ) -> Any:
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
                item = self._to_jsonable(
                    raw_item,
                    warnings=warnings,
                    path=f"{path}.{self._normalize_text(raw_key)}",
                )
                if item is None:
                    continue
                key = self._normalize_text(raw_key)
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
                item = self._to_jsonable(
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
    def _canonicalize_routing_key(raw_key: Any) -> str:
        text = InputNormalizationEngine._normalize_text(raw_key)
        lowered = text.lower()
        return _ROUTING_KEY_ALIASES.get(
            lowered,
            lowered if lowered in _NORMALIZED_ROUTING_KEYS else text,
        )

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()
