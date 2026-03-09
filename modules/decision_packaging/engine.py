"""Final decision packaging engine for unified pipeline outputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
import math
from typing import Any, Dict, List, Mapping, Sequence

from core.contracts import DecisionContract, DecisionPackagingContract


_VALID_OUTCOMES = {
    "accept",
    "accept_with_mitigation",
    "defer",
    "reject",
    "direct_response",
}
_OUTCOME_ALIASES = {
    "support": "accept",
    "oppose": "reject",
    "yes": "accept",
    "no": "reject",
}
_VALID_RECOMMENDATIONS = {"support", "oppose", "defer"}
_RECOMMENDATION_ALIASES = {
    "accept": "support",
    "accept_with_mitigation": "support",
    "reject": "oppose",
    "use_direct_llm_response": "defer",
    "no_council_response": "defer",
}
_VALID_COUNCIL_OUTCOMES = {
    "not_invoked",
    "quick_mode_direct_response",
    "council_disabled_ablation",
    "consensus_reached",
    "deadlocked",
    "bounded_risk_tradeoff",
    "contested",
    "engine_error",
}
_COUNCIL_OUTCOME_ALIASES = {
    "balanced": "bounded_risk_tradeoff",
    "consensus": "consensus_reached",
    "quick_mode": "quick_mode_direct_response",
}
_VALID_MODES = {"baseline", "quick", "meeting", "war", "darbar"}
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


def _coerce_mapping_like(value: Any) -> Dict[str, Any] | None:
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
        key = DecisionPackagingEngine._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class DecisionPackagingResult:
    """Packaged decision payload and summary contract."""

    package: Dict[str, Any]
    contract: DecisionPackagingContract
    warnings: List[str]


@dataclass
class DecisionPackagingEngine:
    """Builds a stable final decision package from pipeline stage outputs."""

    def package(
        self,
        *,
        decision_contract: DecisionContract | None,
        prime_decision: Mapping[str, Any] | Any | None,
        council_result: Mapping[str, Any] | Any | None,
        knowledge_result: Mapping[str, Any] | Any | None,
        mode: Any = None,
    ) -> DecisionPackagingResult:
        warnings: List[str] = []
        decision = decision_contract or DecisionContract(decision="defer", mode="meeting")

        prime_payload = self._coerce_mapping(
            prime_decision,
            warnings=warnings,
            field_name="prime_decision",
        )
        council_payload = self._coerce_mapping(
            council_result,
            warnings=warnings,
            field_name="council_result",
        )
        knowledge_payload = self._coerce_mapping(
            knowledge_result,
            warnings=warnings,
            field_name="knowledge_result",
        )

        final_outcome = self._normalize_outcome(
            self._read_mapping_field(
                prime_payload,
                ("final_outcome",),
                default=decision.decision,
            ),
            warnings=warnings,
        )
        recommendation = self._normalize_recommendation(
            self._read_mapping_field(
                council_payload,
                ("recommendation",),
                default="defer",
            ),
            warnings=warnings,
        )
        council_outcome = self._normalize_council_outcome(
            self._read_mapping_field(
                council_payload,
                ("outcome",),
                default="not_invoked",
            ),
            warnings=warnings,
        )
        decision_mode = self._normalize_mode(
            mode
            or decision.mode
            or self._read_mapping_field(prime_payload, ("mode",))
            or "meeting",
            warnings=warnings,
        )

        reason = str(
            self._read_mapping_field(prime_payload, ("reason",))
            or decision.rationale
            or ""
        ).strip()
        if not reason:
            reason = "decision_reason_unavailable"
            warnings.append("Missing prime decision reason normalized to placeholder.")

        confidence = self._normalize_confidence(
            self._read_mapping_field(
                prime_payload,
                ("confidence",),
                default=decision.confidence,
            ),
            warnings=warnings,
            field_name="decision_confidence",
        )

        red_lines = self._normalize_string_list(
            self._read_mapping_field(
                council_payload,
                ("red_line_concerns",),
                default=[],
            ),
            warnings=warnings,
            field_name="red_line_concerns",
            lowercase=True,
        )
        knowledge_items = self._normalize_knowledge_items(
            knowledge_payload,
            warnings=warnings,
        )

        explicit_followup = self._to_bool(
            self._read_mapping_field(
                prime_payload,
                ("requires_followup",),
                default=self._read_mapping_field(council_payload, ("requires_followup",)),
            )
        )
        requires_followup = (
            explicit_followup
            if explicit_followup is not None
            else self._derive_requires_followup(
                final_outcome=final_outcome,
                council_outcome=council_outcome,
                red_line_count=len(red_lines),
            )
        )

        package = {
            "final_outcome": final_outcome,
            "reason": reason,
            "confidence": confidence,
            "mode": decision_mode,
            "recommendation": recommendation,
            "council_outcome": council_outcome,
            "red_line_concerns": red_lines,
            "knowledge_items_used": len(knowledge_items),
            "requires_followup": bool(requires_followup),
            "source": "decision_packaging",
        }

        deduped_warnings = self._dedupe_warnings(warnings)
        contract = DecisionPackagingContract(
            final_outcome=final_outcome,
            mode=decision_mode,
            confidence=confidence,
            recommendation=recommendation,
            council_outcome=council_outcome,
            red_line_count=len(red_lines),
            knowledge_item_count=len(knowledge_items),
            requires_followup=bool(requires_followup),
            warning_count=len(deduped_warnings),
            source="decision_packaging",
        )
        return DecisionPackagingResult(
            package=package,
            contract=contract,
            warnings=deduped_warnings,
        )

    @staticmethod
    def _coerce_mapping(
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
    ) -> Dict[str, Any]:
        if value is None:
            return {}
        mapping_like = _coerce_mapping_like(value)
        if mapping_like is not None:
            return mapping_like
        if isinstance(value, (str, bytes, bytearray)):
            text = DecisionPackagingEngine._normalize_text(value)
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
                return {}
            parsed_mapping = _coerce_mapping_like(parsed)
            if parsed_mapping is not None:
                warnings.append(f"String {field_name} payload normalized from JSON mapping.")
                return parsed_mapping
            warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
            return {}
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
            return {}

        result: Dict[str, Any] = {}
        extracted = False
        for key in (
            "final_outcome",
            "reason",
            "confidence",
            "mode",
            "recommendation",
            "outcome",
            "red_line_concerns",
            "requires_followup",
            "synthesized_knowledge",
        ):
            if not hasattr(value, key):
                continue
            result[key] = getattr(value, key)
            extracted = True

        if extracted:
            warnings.append(f"Non-mapping {field_name} normalized from object attributes.")
            return result

        warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
        return {}

    @staticmethod
    def _normalize_outcome(value: Any, *, warnings: List[str]) -> str:
        raw = DecisionPackagingEngine._normalize_text(value or "defer").lower()
        normalized = _OUTCOME_ALIASES.get(raw, raw)
        if normalized in _VALID_OUTCOMES:
            return normalized
        warnings.append(f"Unsupported final_outcome '{raw}' normalized to 'defer'.")
        return "defer"

    @staticmethod
    def _normalize_recommendation(value: Any, *, warnings: List[str]) -> str:
        raw = DecisionPackagingEngine._normalize_text(value or "defer").lower()
        normalized = _RECOMMENDATION_ALIASES.get(raw, raw)
        if normalized in _VALID_RECOMMENDATIONS:
            return normalized
        warnings.append(f"Unsupported recommendation '{raw}' normalized to 'defer'.")
        return "defer"

    @staticmethod
    def _normalize_council_outcome(value: Any, *, warnings: List[str]) -> str:
        raw = DecisionPackagingEngine._normalize_text(value or "not_invoked").lower()
        normalized = _COUNCIL_OUTCOME_ALIASES.get(raw, raw)
        if normalized in _VALID_COUNCIL_OUTCOMES:
            if normalized != raw:
                warnings.append(f"Council outcome alias '{raw}' normalized to '{normalized}'.")
            return normalized
        warnings.append(f"Unsupported council_outcome '{raw}' normalized to 'not_invoked'.")
        return "not_invoked"

    @staticmethod
    def _normalize_mode(value: Any, *, warnings: List[str]) -> str:
        raw = DecisionPackagingEngine._normalize_text(value or "meeting").lower()
        normalized = _MODE_ALIASES.get(raw, raw)
        if normalized in _VALID_MODES:
            if normalized != raw:
                warnings.append(f"Mode alias '{raw}' normalized to '{normalized}'.")
            return normalized
        warnings.append(f"Unsupported packaging mode '{raw}' normalized to 'meeting'.")
        return "meeting"

    @staticmethod
    def _normalize_confidence(
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
    ) -> float:
        try:
            numeric = float(value)
        except Exception:
            warnings.append(f"Invalid {field_name} normalized to 0.0.")
            return 0.0
        if not math.isfinite(numeric):
            warnings.append(f"Non-finite {field_name} normalized to 0.0.")
            return 0.0
        if numeric < 0.0:
            warnings.append(f"{field_name} below 0.0 clamped to 0.0.")
            return 0.0
        if numeric > 1.0:
            warnings.append(f"{field_name} above 1.0 clamped to 1.0.")
            return 1.0
        return numeric

    @staticmethod
    def _normalize_string_list(
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
        lowercase: bool,
    ) -> List[str]:
        if value in (None, ""):
            return []
        if isinstance(value, (bytes, bytearray)):
            raw = [DecisionPackagingEngine._normalize_text(value)]
        elif isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [DecisionPackagingEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    f"{field_name} iterable iteration failed; partial values preserved."
                )
        elif isinstance(value, Mapping):
            warnings.append(f"Invalid {field_name} payload normalized to empty list.")
            return []
        elif isinstance(value, Iterable):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [DecisionPackagingEngine._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    f"{field_name} iterable iteration failed; partial values preserved."
                )
        else:
            warnings.append(f"Invalid {field_name} payload normalized to empty list.")
            return []

        normalized: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            text = item.lower() if lowercase else item
            if text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    def _normalize_knowledge_items(
        self,
        knowledge_payload: Mapping[str, Any],
        *,
        warnings: List[str],
    ) -> List[str]:
        source = self._read_mapping_field(knowledge_payload, ("synthesized_knowledge",))
        if source in (None, ""):
            source = self._read_mapping_field(knowledge_payload, ("synthesized_items",), default=[])
        if isinstance(source, (bytes, bytearray)):
            items = [self._normalize_text(source)]
        elif isinstance(source, str):
            items = [source]
        elif isinstance(source, Sequence) and not isinstance(source, (bytes, bytearray)):
            raw_items, failed = _coerce_iterable_items(source, preserve_partial=True)
            items = [self._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    "synthesized_knowledge iterable iteration failed; partial values preserved."
                )
        elif isinstance(source, Iterable) and not isinstance(source, Mapping):
            raw_items, failed = _coerce_iterable_items(source, preserve_partial=True)
            items = [self._normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    "synthesized_knowledge iterable iteration failed; partial values preserved."
                )
        elif source in (None, ""):
            items = []
        else:
            warnings.append("Invalid synthesized_knowledge payload normalized to empty list.")
            items = []

        normalized: List[str] = []
        seen = set()
        for item in items:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _derive_requires_followup(
        *,
        final_outcome: str,
        council_outcome: str,
        red_line_count: int,
    ) -> bool:
        return (
            final_outcome in {"defer", "reject", "accept_with_mitigation"}
            or red_line_count > 0
            or council_outcome in {"deadlocked", "bounded_risk_tradeoff"}
        )

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        if isinstance(value, str):
            text = value.strip().lower()
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
            DecisionPackagingEngine._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _read_mapping_field(
        mapping: Mapping[str, Any],
        keys: Sequence[str],
        *,
        default: Any = None,
    ) -> Any:
        if not isinstance(mapping, Mapping):
            return default
        normalized_targets = {
            DecisionPackagingEngine._normalize_key_name(key)
            for key in keys
        }
        try:
            source_items = mapping.items()
        except Exception:
            return default
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
        for raw_key, value in items:
            if DecisionPackagingEngine._normalize_key_name(raw_key) in normalized_targets:
                return value
        return default

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
