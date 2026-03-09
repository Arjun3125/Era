"""Engine for normalized knowledge synthesis contract generation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from core.contracts import KnowledgeContract
from persona.knowledge_engine import synthesize_knowledge

_MODE_DEFAULT_MAX_ITEMS = {
    "baseline": 4,
    "quick": 5,
    "meeting": 10,
    "war": 10,
    "darbar": 12,
}

_MODE_ALIASES = {
    "quick_mode": "quick",
    "fast": "quick",
    "normal": "meeting",
    "standard": "meeting",
    "default": "meeting",
    "war_mode": "war",
    "full_council": "darbar",
    "board": "darbar",
}


def _coerce_iterable_items(
    value: Any,
    *,
    preserve_partial: bool,
) -> tuple[List[Any], bool]:
    try:
        iterator = iter(value)
    except Exception:
        return [], True
    items: List[Any] = []
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


def _coerce_mapping_like(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        try:
            items = list(value.items())
        except Exception:
            return {}
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
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
        key = KnowledgeSynthesisEngine._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class KnowledgeSynthesisResult:
    """Structured output from knowledge synthesis execution."""

    knowledge_contract: KnowledgeContract
    knowledge_result: Dict[str, Any]
    warnings: List[str]


@dataclass
class KnowledgeSynthesisInputs:
    """Normalized synthesis inputs derived from routing context."""

    active_domains: List[str]
    domain_confidence: float
    max_items: int
    extra_context: List[str]
    warnings: List[str]


@dataclass
class KnowledgeSynthesisEngine:
    """Adapter over persona knowledge synthesis with typed contracts."""

    default_max_items: int = 5
    default_domain_confidence: float = 0.75
    max_items_upper_bound: int = 50
    max_extra_context_items: int = 20
    max_extra_context_chars: int = 2000

    def run(
        self,
        *,
        user_input: str,
        active_domains: List[str],
        domain_confidence: float,
        max_items: Optional[int] = None,
        extra_context: Optional[List[str]] = None,
    ) -> KnowledgeSynthesisResult:
        warnings: List[str] = []
        normalized_user_input = self._normalize_text(user_input)
        if not normalized_user_input:
            warnings.append("Empty user_input normalized to placeholder text.")
            normalized_user_input = "No user input provided."

        normalized_domains = self._normalize_domains(active_domains, warnings=warnings)
        if not normalized_domains:
            normalized_domains = ["strategy"]
            warnings.append("active_domains missing; defaulted to ['strategy'].")

        normalized_confidence = self._normalize_domain_confidence(
            domain_confidence,
            warnings=warnings,
        )
        normalized_max_items = self._normalize_max_items(
            max_items=max_items,
            mode=None,
            warnings=warnings,
        )
        normalized_extra_context = self._normalize_extra_context(
            extra_context,
            warnings=warnings,
        )

        try:
            result = synthesize_knowledge(
                user_input=normalized_user_input,
                active_domains=list(normalized_domains),
                domain_confidence=float(normalized_confidence),
                max_items=int(normalized_max_items),
                extra_context=list(normalized_extra_context),
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            warnings.append(f"synthesize_knowledge failed: {type(exc).__name__}: {exc}")
            result = {
                "synthesized_knowledge": [],
                "knowledge_trace": [],
                "knowledge_quality": {"candidate_quality": 0.0},
                "error": str(exc),
            }

        normalized_result = self._normalize_result_payload(
            result=result,
            active_domains=normalized_domains,
            domain_confidence=normalized_confidence,
            max_items=normalized_max_items,
            warnings=warnings,
        )
        knowledge_contract = KnowledgeContract(
            active_domains=list(normalized_result.get("active_domains", []) or []),
            synthesized_items=list(normalized_result.get("synthesized_knowledge", []) or []),
            trace=list(normalized_result.get("knowledge_trace", []) or []),
            quality=dict(normalized_result.get("knowledge_quality", {}) or {}),
        )
        return KnowledgeSynthesisResult(
            knowledge_contract=knowledge_contract,
            knowledge_result=normalized_result,
            warnings=self._dedupe_warnings(warnings),
        )

    def resolve_inputs(
        self,
        *,
        mode: str,
        routing_context: Mapping[str, Any],
    ) -> KnowledgeSynthesisInputs:
        """Derive stable synthesis inputs from routing context and mode."""
        warnings: List[str] = []
        context = self._coerce_mapping(
            routing_context,
            warnings=warnings,
            field_name="routing_context",
        )
        normalized_mode = self._normalize_mode(mode, warnings)

        domains_raw = context.get("domains") or context.get("active_domains") or []
        active_domains = self._normalize_domains(domains_raw, warnings=warnings)
        if not active_domains:
            active_domains = ["strategy"]
            warnings.append("routing_context domains missing; defaulted to ['strategy'].")

        raw_conf = context.get(
            "domain_confidence",
            context.get("confidence", self.default_domain_confidence),
        )
        domain_confidence = self._normalize_domain_confidence(raw_conf, warnings=warnings)

        raw_max_items = (
            context.get("kis_max_items")
            if "kis_max_items" in context
            else context.get("max_items")
        )
        max_items = self._normalize_max_items(
            max_items=raw_max_items,
            mode=normalized_mode,
            warnings=warnings,
        )

        extra_context = self._normalize_extra_context(
            context.get("extra_context", []),
            warnings=warnings,
        )
        if not extra_context:
            fallback_extra = self._normalize_extra_context(
                context.get("synthesized_knowledge"),
                warnings=warnings,
            )
            if fallback_extra:
                extra_context = fallback_extra
                warnings.append(
                    "extra_context missing; reused routing_context.synthesized_knowledge."
                )

        return KnowledgeSynthesisInputs(
            active_domains=active_domains,
            domain_confidence=domain_confidence,
            max_items=max_items,
            extra_context=extra_context,
            warnings=self._dedupe_warnings(warnings),
        )

    @staticmethod
    def _normalize_domains(value: Any, *, warnings: List[str]) -> List[str]:
        if isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, (bytes, bytearray)):
            raw = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, (list, tuple, set)):
            raw = [KnowledgeSynthesisEngine._normalize_text(item) for item in value]
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [KnowledgeSynthesisEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append("Invalid domains payload ignored during synthesis input normalization.")
        else:
            if value not in (None, "", []):
                warnings.append("Invalid domains payload ignored during synthesis input normalization.")
            return []

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

    def _normalize_domain_confidence(self, value: Any, *, warnings: List[str]) -> float:
        try:
            score = float(value)
        except Exception:
            warnings.append("Invalid domain_confidence normalized to default value.")
            return self.default_domain_confidence

        if not math.isfinite(score):
            warnings.append("Non-finite domain_confidence normalized to default value.")
            return self.default_domain_confidence
        if score < 0.0:
            warnings.append("Negative domain_confidence clamped to 0.0.")
            return 0.0
        if score > 1.0:
            warnings.append("domain_confidence above 1.0 clamped to 1.0.")
            return 1.0
        return score

    def _normalize_max_items(
        self,
        *,
        max_items: Any,
        mode: str | None,
        warnings: List[str],
    ) -> int:
        if max_items is None:
            if mode:
                default_mode = self._normalize_text(mode).lower()
                return int(_MODE_DEFAULT_MAX_ITEMS.get(default_mode, self.default_max_items))
            return int(self.default_max_items)
        try:
            value = int(max_items)
        except Exception:
            warnings.append("Invalid kis_max_items normalized to default.")
            if mode:
                return int(_MODE_DEFAULT_MAX_ITEMS.get(self._normalize_text(mode).lower(), self.default_max_items))
            return int(self.default_max_items)
        if value < 1:
            warnings.append("kis_max_items below 1 normalized to 1.")
            return 1
        if value > int(self.max_items_upper_bound):
            warnings.append(
                f"kis_max_items above {self.max_items_upper_bound} clamped to upper bound."
            )
            return int(self.max_items_upper_bound)
        return value

    def _normalize_extra_context(self, value: Any, *, warnings: List[str]) -> List[str]:
        if value in (None, ""):
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [bytes(value).decode("utf-8", errors="replace")]
        elif isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        elif isinstance(value, Iterable) and not isinstance(value, Mapping):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            if failed:
                warnings.append("Invalid extra_context payload normalized to empty list.")
        else:
            warnings.append("Invalid extra_context payload normalized to empty list.")
            return []

        normalized: List[str] = []
        seen = set()
        for raw_item in raw_items:
            item = self._to_jsonable(
                raw_item,
                warnings=warnings,
                path="extra_context.item",
            )
            if item is None:
                continue
            if isinstance(item, str):
                text = item.strip()
            else:
                try:
                    text = json.dumps(item, ensure_ascii=False, sort_keys=True)
                except Exception:
                    text = str(item).strip()

            if not text:
                continue
            if len(text) > self.max_extra_context_chars:
                text = text[: self.max_extra_context_chars].rstrip() + "..."
                warnings.append("extra_context item exceeded max length and was truncated.")

            if text in seen:
                continue
            seen.add(text)
            normalized.append(text)
            if len(normalized) >= self.max_extra_context_items:
                warnings.append("extra_context exceeded max items and was truncated.")
                break
        return normalized

    def _normalize_mode(self, value: Any, warnings: List[str]) -> str:
        raw = self._normalize_text(value).lower() or "meeting"
        normalized = _MODE_ALIASES.get(raw, raw)
        if normalized in _MODE_DEFAULT_MAX_ITEMS:
            return normalized
        if raw:
            warnings.append(f"Unsupported mode '{raw}' normalized to 'meeting'.")
        return "meeting"

    def _normalize_result_payload(
        self,
        *,
        result: Any,
        active_domains: List[str],
        domain_confidence: float,
        max_items: int,
        warnings: List[str],
    ) -> Dict[str, Any]:
        payload = self._coerce_mapping(result, warnings=warnings, field_name="knowledge_result")

        synthesized_raw = payload.get("synthesized_knowledge", [])
        if isinstance(synthesized_raw, str):
            synthesized_candidates = [synthesized_raw]
            warnings.append("knowledge_result.synthesized_knowledge normalized from string to list.")
        elif isinstance(synthesized_raw, (list, tuple, set)):
            synthesized_candidates = list(synthesized_raw)
        elif isinstance(synthesized_raw, Iterable) and not isinstance(
            synthesized_raw, Mapping
        ):
            synthesized_candidates, failed = _coerce_iterable_items(
                synthesized_raw,
                preserve_partial=True,
            )
            if failed:
                warnings.append("knowledge_result.synthesized_knowledge normalized to list.")
        elif synthesized_raw in (None, ""):
            synthesized_candidates = []
        else:
            synthesized_candidates = [synthesized_raw]
            warnings.append("knowledge_result.synthesized_knowledge normalized to list.")

        synthesized: List[str] = []
        seen_synthesized = set()
        for item in synthesized_candidates:
            text = str(item).strip()
            if not text or text in seen_synthesized:
                continue
            seen_synthesized.add(text)
            synthesized.append(text)

        trace_raw = payload.get("knowledge_trace", [])
        if isinstance(trace_raw, Mapping):
            trace_candidates = [trace_raw]
            warnings.append("knowledge_result.knowledge_trace normalized from dict to list.")
        elif isinstance(trace_raw, (list, tuple, set)):
            trace_candidates = list(trace_raw)
        elif isinstance(trace_raw, Iterable) and not isinstance(trace_raw, (str, bytes, bytearray, Mapping)):
            trace_candidates, failed = _coerce_iterable_items(
                trace_raw,
                preserve_partial=True,
            )
            if failed:
                warnings.append("knowledge_result.knowledge_trace normalized to list.")
        elif trace_raw in (None, ""):
            trace_candidates = []
        else:
            trace_candidates = []
            warnings.append("knowledge_result.knowledge_trace normalized to list.")

        trace: List[Dict[str, Any]] = []
        for item in trace_candidates:
            mapping_item = self._coerce_mapping(
                item,
                warnings=warnings,
                field_name="knowledge_trace.item",
            )
            if not mapping_item:
                continue
            sanitized_item = self._sanitize_mapping(
                mapping_item,
                warnings=warnings,
                path="knowledge_trace.item",
            )
            if sanitized_item:
                trace.append(sanitized_item)

        quality_raw = self._coerce_mapping(
            payload.get("knowledge_quality", {}),
            warnings=warnings,
            field_name="knowledge_quality",
        )
        quality = self._sanitize_mapping(
            quality_raw,
            warnings=warnings,
            path="knowledge_quality",
        )

        candidate_quality = self._safe_float(
            quality.get("candidate_quality", 0.0),
            fallback=0.0,
            warnings=warnings,
            field_name="knowledge_quality.candidate_quality",
        )
        candidate_quality = max(0.0, min(1.0, candidate_quality))
        quality["candidate_quality"] = candidate_quality

        avg_kis = self._safe_float(
            quality.get("avg_kis", 0.0),
            fallback=0.0,
            warnings=warnings,
            field_name="knowledge_quality.avg_kis",
        )
        quality["avg_kis"] = avg_kis

        top_kis = quality.get("top_kis", [])
        normalized_top_kis: List[float] = []
        if isinstance(top_kis, (list, tuple, set)):
            for idx, value in enumerate(list(top_kis)):
                numeric = self._safe_float(
                    value,
                    fallback=None,
                    warnings=warnings,
                    field_name=f"knowledge_quality.top_kis[{idx}]",
                )
                if numeric is None:
                    continue
                normalized_top_kis.append(numeric)
        elif top_kis not in (None, ""):
            warnings.append("knowledge_quality.top_kis normalized to list.")
        if normalized_top_kis:
            quality["top_kis"] = normalized_top_kis
        else:
            quality["top_kis"] = []

        debug_payload = self._coerce_mapping(
            payload.get("knowledge_debug", {}),
            warnings=warnings,
            field_name="knowledge_debug",
        )
        knowledge_debug = self._sanitize_mapping(
            debug_payload,
            warnings=warnings,
            path="knowledge_debug",
        )

        normalized = self._sanitize_mapping(payload, warnings=warnings, path="knowledge_result")
        normalized["active_domains"] = list(active_domains)
        normalized["domain_confidence"] = float(domain_confidence)
        normalized["max_items"] = int(max_items)
        normalized["synthesized_knowledge"] = synthesized[:max_items]
        normalized["knowledge_trace"] = trace[:max_items]
        normalized["knowledge_quality"] = quality
        normalized["knowledge_debug"] = knowledge_debug
        return normalized

    def _coerce_mapping(
        self,
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
    ) -> Dict[str, Any]:
        mapping_like = _coerce_mapping_like(value)
        if mapping_like is not None:
            return mapping_like
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
                warnings.append(f"Invalid {field_name} string ignored.")
                return {}
            parsed_mapping = _coerce_mapping_like(parsed)
            if parsed_mapping is not None:
                return parsed_mapping
            warnings.append(f"Non-dict {field_name} JSON ignored.")
            return {}

        warnings.append(f"Invalid {field_name} payload ignored.")
        return {}

    def _sanitize_mapping(
        self,
        value: Mapping[str, Any],
        *,
        warnings: List[str],
        path: str,
    ) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        try:
            items = value.items()
        except Exception:
            return sanitized
        for key, raw_item in items:
            normalized_key = self._normalize_text(key)
            if not normalized_key:
                continue
            normalized_item = self._to_jsonable(
                raw_item,
                warnings=warnings,
                path=f"{path}.{normalized_key}",
            )
            if normalized_item is None:
                continue
            sanitized[normalized_key] = normalized_item
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
            try:
                items = value.items()
            except Exception:
                return result
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
            for index, raw_item in enumerate(list(value)):
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
    def _safe_float(
        value: Any,
        *,
        fallback: float | None,
        warnings: List[str],
        field_name: str,
    ) -> float | None:
        if value is None:
            return fallback
        try:
            numeric = float(value)
        except Exception:
            warnings.append(f"Invalid {field_name} normalized to fallback.")
            return fallback
        if not math.isfinite(numeric):
            warnings.append(f"Non-finite {field_name} normalized to fallback.")
            return fallback
        return numeric

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

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
