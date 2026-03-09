"""Council result normalization engine for stable prime-decision handoff."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
import math
from typing import Any, Dict, List, Mapping, Sequence

from core.contracts import CouncilNormalizationContract


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
_VALID_STANCES = {"support", "oppose", "neutral"}
_STANCE_SUPPORT_ALIASES = {
    "accept",
    "accept_with_mitigation",
    "support_with_caution",
    "proceed",
    "yes",
}
_STANCE_OPPOSE_ALIASES = {
    "reject",
    "block",
    "no",
}
_DIRECT_OUTCOME_TOKENS = {
    "consensus_reached",
    "bounded_risk_tradeoff",
    "deadlocked",
    "quick_mode_direct_response",
    "council_disabled_ablation",
    "not_invoked",
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


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
        key = _normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class CouncilNormalizationResult:
    """Normalized council payload + summary contract."""

    normalized_council: Dict[str, Any]
    normalized_minister_outputs: Dict[str, Dict[str, Any]]
    council_positions: List[Dict[str, Any]]
    contract: CouncilNormalizationContract
    warnings: List[str]


@dataclass
class CouncilNormalizationEngine:
    """Normalizes heterogeneous council outputs for downstream consumers."""

    def normalize(
        self,
        *,
        council_result: Mapping[str, Any] | Any | None,
        mode: Any = None,
    ) -> CouncilNormalizationResult:
        warnings: List[str] = []
        raw = self._coerce_council_payload(council_result, warnings)

        raw_mode = mode if mode is not None else raw.get("mode")
        mode_value = self._normalize_mode(raw_mode, warnings)

        recommendation_raw = str(raw.get("recommendation", "")).strip().lower()
        source_outcome = str(raw.get("outcome", "")).strip().lower()
        red_line_concerns = self._normalize_string_list(
            raw.get("red_line_concerns", []),
            warnings,
            field_name="red_line_concerns",
            lowercase=True,
        )

        recommendation = self._map_recommendation(recommendation_raw)
        outcome = self._map_outcome(
            source_outcome,
            recommendation=recommendation,
            red_line_count=len(red_line_concerns),
        )

        consensus_strength = self._normalize_probability(
            raw.get("consensus_strength", raw.get("avg_confidence", 0.0)),
            warnings,
            field="consensus_strength",
        )
        reasoning = str(raw.get("reasoning", "") or "").strip()[:1000]

        minister_outputs_raw = (
            raw.get("minister_outputs")
            or raw.get("minister_positions")
            or raw.get("council_positions")
            or {}
        )
        normalized_minister_outputs = self._normalize_minister_outputs(minister_outputs_raw, warnings)
        council_positions = self._build_council_positions(normalized_minister_outputs)

        failed_ministers = self._normalize_string_list(
            raw.get("ministers_failed", []),
            warnings,
            field_name="ministers_failed",
            lowercase=False,
        )

        council_invoked = source_outcome not in {
            "quick_mode_direct_response",
            "council_disabled_ablation",
            "not_invoked",
            "direct_response",
        }

        normalized_council = {
            "outcome": outcome,
            "recommendation": recommendation,
            "avg_confidence": consensus_strength,
            "consensus_strength": consensus_strength,
            "reasoning": reasoning,
            "mode": mode_value,
            "red_line_concerns": red_line_concerns,
            "minister_outputs": normalized_minister_outputs,
            "minister_positions": normalized_minister_outputs,
            "council_positions": council_positions,
            "ministers_failed": failed_ministers,
            "source_outcome": source_outcome,
            "source_recommendation": recommendation_raw,
        }

        deduped_warnings = self._dedupe_warnings(warnings)
        contract = CouncilNormalizationContract(
            mode=mode_value,
            outcome=outcome,
            recommendation=recommendation,
            consensus_strength=consensus_strength,
            minister_count=len(normalized_minister_outputs),
            failed_minister_count=len(failed_ministers),
            red_line_count=len(red_line_concerns),
            council_invoked=council_invoked,
            warning_count=len(deduped_warnings),
            source="council_normalization",
        )
        return CouncilNormalizationResult(
            normalized_council=normalized_council,
            normalized_minister_outputs=normalized_minister_outputs,
            council_positions=council_positions,
            contract=contract,
            warnings=deduped_warnings,
        )

    @staticmethod
    def _coerce_council_payload(value: Any, warnings: List[str]) -> Dict[str, Any]:
        if value is None:
            return {}
        mapping_like = _coerce_mapping_like(value)
        if mapping_like is not None:
            return mapping_like
        if isinstance(value, (str, bytes, bytearray)):
            text = _normalize_text(value)
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                warnings.append("Invalid council payload normalized to empty mapping.")
                return {}
            parsed_mapping = _coerce_mapping_like(parsed)
            if parsed_mapping is not None:
                return parsed_mapping
            warnings.append("Invalid council payload normalized to empty mapping.")
            return {}

        payload: Dict[str, Any] = {}
        extracted = False
        for field in (
            "outcome",
            "recommendation",
            "avg_confidence",
            "consensus_strength",
            "reasoning",
            "mode",
            "minister_positions",
            "minister_outputs",
            "red_line_concerns",
            "ministers_failed",
            "council_positions",
        ):
            if not hasattr(value, field):
                continue
            payload[field] = getattr(value, field)
            extracted = True

        if extracted:
            warnings.append("Non-mapping council payload normalized from object attributes.")
            return payload

        warnings.append("Invalid council payload normalized to empty mapping.")
        return {}

    def _normalize_mode(self, value: Any, warnings: List[str]) -> str:
        raw = _normalize_text(value).lower()
        if not raw:
            return "meeting"
        normalized = _MODE_ALIASES.get(raw, raw)
        if normalized in _VALID_MODES:
            if normalized != raw:
                warnings.append(f"Mode alias '{raw}' normalized to '{normalized}'.")
            return normalized
        warnings.append(f"Unsupported normalization mode '{raw}' normalized to 'meeting'.")
        return "meeting"

    @staticmethod
    def _normalize_probability(value: Any, warnings: List[str], *, field: str) -> float:
        try:
            numeric = float(value)
        except Exception:
            warnings.append(f"Invalid {field} normalized to 0.0.")
            return 0.0
        if not math.isfinite(numeric):
            warnings.append(f"Non-finite {field} normalized to 0.0.")
            return 0.0
        if numeric < 0.0:
            warnings.append(f"{field} below 0.0 clamped to 0.0.")
            return 0.0
        if numeric > 1.0:
            warnings.append(f"{field} above 1.0 clamped to 1.0.")
            return 1.0
        return numeric

    @staticmethod
    def _normalize_minister_outputs(
        minister_outputs: Any,
        warnings: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        if isinstance(minister_outputs, Mapping):
            candidate_items, failed = _coerce_iterable_items(
                minister_outputs.items(),
                preserve_partial=True,
            )
            candidates = {}
            for key, payload in candidate_items:
                if key in candidates:
                    continue
                candidates[key] = payload
            if failed:
                warnings.append(
                    "Minister outputs mapping iteration failed; partial payload preserved."
                )
        elif isinstance(minister_outputs, (bytes, bytearray)):
            candidates = {}
            warnings.append("Invalid minister outputs payload normalized to empty mapping.")
        elif isinstance(minister_outputs, Sequence) and not isinstance(minister_outputs, (str, bytes, bytearray)):
            mapping_like = _coerce_mapping_like(minister_outputs)
            if mapping_like is not None:
                candidates = mapping_like
                warnings.append("Minister outputs iterable key/value payload normalized to mapping.")
            else:
                candidates = {}
                source_items, failed = _coerce_iterable_items(minister_outputs, preserve_partial=True)
                for item in source_items:
                    if not isinstance(item, Mapping):
                        continue
                    name = _normalize_text(item.get("minister", "")).lower()
                    if not name:
                        continue
                    details = _coerce_mapping_like(item) or {}
                    candidates[name] = details
                if candidates:
                    warnings.append("Council positions list normalized into minister output mapping.")
                if failed:
                    warnings.append(
                        "Minister outputs sequence iteration failed; partial payload preserved."
                    )
        elif isinstance(minister_outputs, Iterable):
            seq, seq_failed = _coerce_iterable_items(minister_outputs, preserve_partial=True)
            mapping_like = _coerce_mapping_like(seq)
            if mapping_like is not None:
                candidates = mapping_like
                warnings.append("Minister outputs iterable key/value payload normalized to mapping.")
                if seq_failed:
                    warnings.append(
                        "Minister outputs iterable iteration failed; partial payload preserved."
                    )
            else:
                candidates = {}
                for item in seq:
                    if not isinstance(item, Mapping):
                        continue
                    name = _normalize_text(item.get("minister", "")).lower()
                    if not name:
                        continue
                    details = _coerce_mapping_like(item) or {}
                    candidates[name] = details
                if candidates:
                    warnings.append("Council positions list normalized into minister output mapping.")
                if seq_failed:
                    warnings.append(
                        "Minister outputs iterable iteration failed; partial payload preserved."
                    )
        else:
            candidates = {}
            if minister_outputs not in (None, "", {}):
                warnings.append("Invalid minister outputs payload normalized to empty mapping.")

        normalized: Dict[str, Dict[str, Any]] = {}
        seen = set()
        for key, payload in candidates.items():
            name = _normalize_text(key).lower()
            if not name or name in seen:
                continue
            seen.add(name)

            details_mapping = _coerce_mapping_like(payload)
            details = details_mapping or {}
            if details_mapping is None:
                warnings.append(f"Minister payload for '{name}' was non-mapping and got normalized.")

            stance_raw = _normalize_text(details.get("stance", "neutral")).lower()
            stance = CouncilNormalizationEngine._normalize_stance(stance_raw)
            if stance != stance_raw:
                warnings.append(
                    f"minister[{name}].stance '{stance_raw}' normalized to '{stance}'."
                )

            confidence = CouncilNormalizationEngine._normalize_probability(
                details.get("confidence", 0.0),
                warnings,
                field=f"minister[{name}].confidence",
            )
            reasoning = _normalize_text(details.get("reasoning", ""))[:1000]
            red_line = CouncilNormalizationEngine._parse_bool(
                details.get("red_line_triggered", details.get("red_line", False))
            )

            normalized[name] = {
                "stance": stance,
                "confidence": confidence,
                "reasoning": reasoning,
                "red_line_triggered": bool(red_line),
            }
        return normalized

    @staticmethod
    def _normalize_stance(raw: str) -> str:
        if raw in _VALID_STANCES:
            return raw
        if raw in _STANCE_SUPPORT_ALIASES:
            return "support"
        if raw in _STANCE_OPPOSE_ALIASES:
            return "oppose"
        return "neutral"

    @staticmethod
    def _build_council_positions(
        minister_outputs: Mapping[str, Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        positions: List[Dict[str, Any]] = []
        if not isinstance(minister_outputs, Mapping):
            return positions
        try:
            source_items = minister_outputs.items()
        except Exception:
            return positions
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
        normalized_items: List[tuple[str, Dict[str, Any]]] = []
        for raw_name, raw_details in items:
            name = _normalize_text(raw_name).lower()
            if not name:
                continue
            details_mapping = _coerce_mapping_like(raw_details)
            normalized_items.append((name, details_mapping or {}))

        for name, details in sorted(normalized_items, key=lambda item: item[0]):
            positions.append(
                {
                    "minister": name,
                    "stance": details.get("stance"),
                    "confidence": details.get("confidence"),
                    "reasoning": details.get("reasoning", ""),
                    "red_line_triggered": bool(details.get("red_line_triggered", False)),
                }
            )
        return positions

    @staticmethod
    def _map_outcome(raw_outcome: str, *, recommendation: str, red_line_count: int) -> str:
        if raw_outcome in _DIRECT_OUTCOME_TOKENS:
            return raw_outcome
        if red_line_count > 0:
            return "bounded_risk_tradeoff"
        if recommendation == "support":
            return "consensus_reached"
        if recommendation == "oppose":
            return "bounded_risk_tradeoff"
        return "deadlocked"

    @staticmethod
    def _map_recommendation(raw_recommendation: str) -> str:
        if raw_recommendation in {"support", "oppose", "defer"}:
            return raw_recommendation

        support_tokens = {
            "strong_consensus_support",
            "strong_doctrine_aligned_consensus",
            "aggressive_proceed",
            "proceed_with_confidence",
            "proceed_with_caution",
            "consensus_with_noted_dissent",
            "support_with_caution",
            "accept",
            "accept_with_mitigation",
        }
        oppose_tokens = {
            "strong_consensus_oppose",
            "red_line_blocks_recommendation",
            "red_line_block_override_needed",
            "defensive_hold_or_pivot",
            "reject",
        }
        defer_tokens = {
            "deep_disagreement_defer_decision",
            "mixed_consensus_with_tradeoffs",
            "insufficient_data",
            "unknown_mode",
            "direct_response",
            "no_council_response",
            "use_direct_llm_response",
            "",
        }
        if raw_recommendation in support_tokens:
            return "support"
        if raw_recommendation in oppose_tokens:
            return "oppose"
        if raw_recommendation in defer_tokens:
            return "defer"
        return "defer"

    @staticmethod
    def _normalize_string_list(
        value: Any,
        warnings: List[str],
        *,
        field_name: str,
        lowercase: bool,
    ) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            raw_items = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            source_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [_normalize_text(item) for item in source_items]
            if failed:
                warnings.append(
                    f"{field_name} iterable iteration failed; partial values preserved."
                )
        elif isinstance(value, Mapping):
            warnings.append(f"Invalid {field_name} payload normalized to empty list.")
            return []
        elif isinstance(value, Iterable):
            source_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [_normalize_text(item) for item in source_items]
            if failed:
                warnings.append(
                    f"{field_name} iterable iteration failed; partial values preserved."
                )
        else:
            warnings.append(f"Invalid {field_name} payload normalized to empty list.")
            return []

        normalized: List[str] = []
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
    def _parse_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = _normalize_text(value).lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return None

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
