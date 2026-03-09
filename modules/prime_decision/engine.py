"""Normalized Prime decision engine over ``PrimeConfident``."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
import math
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from core.contracts import DecisionContract


PrimeFactory = Callable[[float, Optional[Any]], Any]


def _default_prime_factory(risk_threshold: float, llm_adapter: Optional[Any]) -> Any:
    from sovereign.prime_confident import PrimeConfident

    return PrimeConfident(risk_threshold=risk_threshold, llm_adapter=llm_adapter)


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
class PrimeDecisionResult:
    """Structured result from prime finalization."""

    final_decision: Dict[str, Any]
    decision_contract: DecisionContract
    normalized_council: Dict[str, Any]
    normalized_minister_outputs: Dict[str, Dict[str, Any]]
    warnings: List[str]


@dataclass
class PrimeDecisionEngine:
    """Adapter that normalizes council outputs before PrimeConfident execution."""

    risk_threshold: float = 0.7
    llm_adapter: Optional[Any] = None
    prime_decider: Optional[Any] = None
    prime_factory: PrimeFactory = _default_prime_factory

    def get_prime_decider(self) -> Any:
        if self.prime_decider is None:
            self.prime_decider = self.prime_factory(self.risk_threshold, self.llm_adapter)
        return self.prime_decider

    def evaluate(
        self,
        *,
        council_recommendation: Any,
        minister_outputs: Optional[Mapping[str, Any] | Sequence[Any]] = None,
        mode: Optional[str] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> PrimeDecisionResult:
        """Return final decision plus normalized contracts."""
        warnings: List[str] = []

        council_payload, council_warnings = self._normalize_council_recommendation(
            council_recommendation
        )
        warnings.extend(council_warnings)

        minister_source = (
            minister_outputs
            if minister_outputs is not None
            else council_payload.pop("_raw_minister_outputs", {})
        )
        normalized_minister_outputs, minister_warnings = self._normalize_minister_outputs(
            minister_source
        )
        warnings.extend(minister_warnings)

        mode_value = self._normalize_mode(
            mode or council_payload.get("mode"),
            warnings=warnings,
        )

        bypass = self._bypass_decision_if_applicable(council_payload, mode_value)
        if bypass is not None:
            final_decision = bypass
        else:
            try:
                prime = self.get_prime_decider()
                decided = prime.decide(council_payload, normalized_minister_outputs)
                if isinstance(decided, Mapping):
                    final_decision = dict(decided)
                else:
                    warnings.append("Prime decider returned non-mapping payload; normalized to fallback.")
                    final_decision = {
                        "final_outcome": "defer",
                        "reason": "prime_decider_invalid_payload",
                    }
            except Exception as exc:  # pragma: no cover - defensive branch
                warnings.append(f"Prime decider failed: {type(exc).__name__}: {exc}")
                final_decision = {
                    "final_outcome": "defer",
                    "reason": "prime_decider_exception",
                }

        final_decision = self._normalize_final_decision(
            final_decision,
            council_payload=council_payload,
            mode=mode_value,
            warnings=warnings,
        )
        confidence = self._derive_confidence(
            final_decision,
            council_payload,
            warnings=warnings,
        )
        final_decision["confidence"] = confidence

        context_keys = self._normalize_context_keys(context, warnings)
        deduped_warnings = self._dedupe_warnings(warnings)

        decision_contract = DecisionContract(
            decision=str(final_decision.get("final_outcome", "defer")),
            confidence=confidence,
            rationale=str(final_decision.get("reason", "")),
            mode=mode_value,
            metadata={
                "council_outcome": council_payload.get("outcome"),
                "council_recommendation": council_payload.get("recommendation"),
                "context_keys": context_keys,
                "warning_count": len(deduped_warnings),
            },
        )

        return PrimeDecisionResult(
            final_decision=final_decision,
            decision_contract=decision_contract,
            normalized_council=council_payload,
            normalized_minister_outputs=normalized_minister_outputs,
            warnings=deduped_warnings,
        )

    def decide(
        self,
        *,
        council_recommendation: Any,
        minister_outputs: Optional[Mapping[str, Any] | Sequence[Any]] = None,
        mode: Optional[str] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compatibility helper returning just the final decision payload."""
        return self.evaluate(
            council_recommendation=council_recommendation,
            minister_outputs=minister_outputs,
            mode=mode,
            context=context,
        ).final_decision

    @staticmethod
    def _normalize_council_recommendation(council: Any) -> tuple[Dict[str, Any], List[str]]:
        """Normalize legacy or module council structures for PrimeConfident."""
        warnings: List[str] = []
        raw = PrimeDecisionEngine._as_council_dict(council)
        raw_mode = _normalize_text(raw.get("mode")).lower()

        recommendation_raw = _normalize_text(raw.get("recommendation", "")).lower()
        outcome_raw = _normalize_text(raw.get("outcome", "")).lower()

        red_line_concerns = PrimeDecisionEngine._normalize_string_list(
            raw.get("red_line_concerns", []),
            warnings=warnings,
            field_name="red_line_concerns",
            lowercase=True,
        )

        mapped_recommendation = PrimeDecisionEngine._map_recommendation(recommendation_raw)
        mapped_outcome = PrimeDecisionEngine._map_outcome(
            outcome_raw,
            mapped_recommendation,
            red_line_count=len(red_line_concerns),
        )
        consensus_strength = PrimeDecisionEngine._normalize_confidence_value(
            raw.get("consensus_strength", 0.0),
            warnings=warnings,
            field_name="consensus_strength",
        )
        avg_confidence = PrimeDecisionEngine._normalize_confidence_value(
            raw.get("avg_confidence", raw.get("confidence", consensus_strength)),
            warnings=warnings,
            field_name="avg_confidence",
        )
        reasoning = _normalize_text(raw.get("reasoning", ""))[:1000]

        normalized = {
            "outcome": mapped_outcome,
            "recommendation": mapped_recommendation,
            "avg_confidence": avg_confidence,
            "consensus_strength": consensus_strength,
            "reasoning": reasoning,
            "mode": raw_mode or "meeting",
            "red_line_concerns": red_line_concerns,
            "source_outcome": outcome_raw,
            "source_recommendation": recommendation_raw,
            "_raw_minister_outputs": raw.get("minister_outputs")
            or raw.get("minister_positions")
            or raw.get("council_positions")
            or {},
        }
        return normalized, PrimeDecisionEngine._dedupe_warnings(warnings)

    @staticmethod
    def _normalize_minister_outputs(
        minister_outputs: Mapping[str, Any] | Sequence[Any] | Any,
    ) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
        warnings: List[str] = []

        if isinstance(minister_outputs, Mapping):
            raw_items, failed = _coerce_iterable_items(
                minister_outputs.items(),
                preserve_partial=True,
            )
            if failed:
                warnings.append(
                    "Minister outputs mapping iteration failed; partial payload preserved."
                )
        elif isinstance(minister_outputs, (str, bytes, bytearray)):
            text = _normalize_text(minister_outputs)
            if not text:
                raw_items = []
            else:
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = None
                if parsed is None:
                    raw_items = []
                    warnings.append("Invalid minister_outputs payload normalized to empty mapping.")
                else:
                    parsed_mapping = _coerce_mapping_like(parsed)
                    if parsed_mapping is not None:
                        raw_items, failed = _coerce_iterable_items(
                            parsed_mapping.items(),
                            preserve_partial=True,
                        )
                        warnings.append("Minister outputs JSON payload normalized to mapping.")
                        if failed:
                            warnings.append(
                                "Minister outputs JSON mapping iteration failed; partial payload preserved."
                            )
                    else:
                        raw_items, failed = PrimeDecisionEngine._extract_minister_items_from_sequence(
                            parsed
                        )
                        if raw_items:
                            warnings.append(
                                "Minister outputs list normalized to mapping by minister key."
                            )
                            if failed:
                                warnings.append(
                                    "Minister outputs sequence iteration failed; partial payload preserved."
                                )
                        else:
                            warnings.append(
                                "Invalid minister_outputs payload normalized to empty mapping."
                            )
        elif isinstance(minister_outputs, Sequence) and not isinstance(
            minister_outputs, (str, bytes, bytearray)
        ):
            mapping_like = _coerce_mapping_like(minister_outputs)
            if mapping_like is not None:
                raw_items, failed = _coerce_iterable_items(
                    mapping_like.items(),
                    preserve_partial=True,
                )
                warnings.append("Minister outputs iterable key/value payload normalized to mapping.")
                if failed:
                    warnings.append(
                        "Minister outputs mapping iteration failed; partial payload preserved."
                    )
            else:
                raw_items, failed = PrimeDecisionEngine._extract_minister_items_from_sequence(
                    minister_outputs
                )
                if raw_items:
                    warnings.append("Minister outputs list normalized to mapping by minister key.")
                    if failed:
                        warnings.append(
                            "Minister outputs sequence iteration failed; partial payload preserved."
                        )
                else:
                    raw_items = []
        elif isinstance(minister_outputs, Iterable):
            seq, seq_failed = _coerce_iterable_items(minister_outputs, preserve_partial=True)
            mapping_like = _coerce_mapping_like(seq)
            if mapping_like is not None:
                raw_items, mapping_failed = _coerce_iterable_items(
                    mapping_like.items(),
                    preserve_partial=True,
                )
                warnings.append("Minister outputs iterable key/value payload normalized to mapping.")
                if seq_failed or mapping_failed:
                    warnings.append(
                        "Minister outputs iterable iteration failed; partial payload preserved."
                    )
            else:
                raw_items, item_failed = PrimeDecisionEngine._extract_minister_items_from_sequence(seq)
                if raw_items:
                    warnings.append("Minister outputs list normalized to mapping by minister key.")
                    if seq_failed or item_failed:
                        warnings.append(
                            "Minister outputs iterable iteration failed; partial payload preserved."
                        )
                else:
                    raw_items = []
        else:
            raw_items = []
            if minister_outputs not in (None, "", {}):
                warnings.append("Invalid minister_outputs payload normalized to empty mapping.")

        normalized: Dict[str, Dict[str, Any]] = {}
        seen = set()
        for raw_name, payload in raw_items:
            name = _normalize_text(raw_name).lower()
            if not name or name in seen:
                continue
            seen.add(name)

            details = PrimeDecisionEngine._as_minister_dict(payload)
            stance_raw = _normalize_text(details.get("stance", "neutral")).lower()
            stance = PrimeDecisionEngine._normalize_minister_stance(stance_raw)
            if stance != stance_raw:
                warnings.append(
                    f"{name}:unsupported stance '{stance_raw}' normalized to '{stance}'."
                )
            normalized[name] = {
                "stance": stance,
                "confidence": PrimeDecisionEngine._normalize_confidence_value(
                    details.get("confidence", 0.0),
                    warnings=warnings,
                    field_name=f"{name}.confidence",
                ),
                "reasoning": _normalize_text(details.get("reasoning", ""))[:1000],
                "red_line_triggered": bool(
                    PrimeDecisionEngine._to_bool(
                        details.get("red_line_triggered", details.get("red_line", False))
                    )
                ),
            }
        return normalized, PrimeDecisionEngine._dedupe_warnings(warnings)

    @staticmethod
    def _extract_minister_items_from_sequence(value: Any) -> tuple[List[tuple[str, Any]], bool]:
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes, bytearray, Mapping)):
            return [], False
        items: List[tuple[str, Any]] = []
        source, failed = _coerce_iterable_items(value, preserve_partial=True)
        for item in source:
            if not isinstance(item, Mapping):
                continue
            name = _normalize_text(item.get("minister", item.get("name", "")))
            if not name:
                continue
            items.append((name, item))
        return items, failed

    @staticmethod
    def _bypass_decision_if_applicable(
        council_payload: Dict[str, Any], mode: str
    ) -> Optional[Dict[str, Any]]:
        source_outcome = _normalize_text(council_payload.get("source_outcome", "")).lower()
        source_recommendation = _normalize_text(council_payload.get("source_recommendation", "")).lower()
        recommendation = _normalize_text(council_payload.get("recommendation", "")).lower()

        if source_outcome == "quick_mode_direct_response" or mode in {"quick", "baseline"}:
            return {
                "final_outcome": "direct_response",
                "reason": "quick_mode_bypass",
                "confidence": float(council_payload.get("avg_confidence", 0.0) or 0.0),
                "details": {"mode": mode},
            }
        if source_outcome == "council_disabled_ablation":
            return {
                "final_outcome": "defer",
                "reason": "council_disabled_ablation",
                "confidence": float(council_payload.get("avg_confidence", 0.0) or 0.0),
            }

        if recommendation == "defer" and source_recommendation in {
            "no_council_response",
            "use_direct_llm_response",
        }:
            return {
                "final_outcome": "defer",
                "reason": source_recommendation,
                "confidence": float(council_payload.get("avg_confidence", 0.0) or 0.0),
            }
        return None

    @staticmethod
    def _map_outcome(
        raw_outcome: str,
        mapped_recommendation: str,
        *,
        red_line_count: int,
    ) -> str:
        if raw_outcome in {
            "consensus_reached",
            "bounded_risk_tradeoff",
            "deadlocked",
            "quick_mode_direct_response",
            "council_disabled_ablation",
            "not_invoked",
        }:
            return raw_outcome

        if red_line_count > 0:
            return "bounded_risk_tradeoff"

        if mapped_recommendation == "support":
            return "consensus_reached"
        if mapped_recommendation == "oppose":
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
    def _derive_confidence(
        final_decision: Dict[str, Any],
        council_payload: Dict[str, Any],
        *,
        warnings: List[str],
    ) -> float:
        llm_assessment = final_decision.get("llm_assessment")
        if isinstance(llm_assessment, Mapping) and "score" in llm_assessment:
            return PrimeDecisionEngine._normalize_confidence_value(
                llm_assessment.get("score"),
                warnings=warnings,
                field_name="llm_assessment.score",
            )
        if "confidence" in final_decision:
            return PrimeDecisionEngine._normalize_confidence_value(
                final_decision.get("confidence"),
                warnings=warnings,
                field_name="final_decision.confidence",
            )
        return PrimeDecisionEngine._normalize_confidence_value(
            council_payload.get("avg_confidence", 0.0),
            warnings=warnings,
            field_name="council.avg_confidence",
        )

    @staticmethod
    def _as_council_dict(value: Any) -> Dict[str, Any]:
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
                return {}
            parsed_mapping = _coerce_mapping_like(parsed)
            if parsed_mapping is not None:
                return parsed_mapping
            return {}

        result: Dict[str, Any] = {}
        for name in (
            "outcome",
            "recommendation",
            "avg_confidence",
            "consensus_strength",
            "reasoning",
            "mode",
            "minister_positions",
            "minister_outputs",
            "red_line_concerns",
            "council_positions",
        ):
            if hasattr(value, name):
                result[name] = getattr(value, name)
        return result

    @staticmethod
    def _as_minister_dict(value: Any) -> Dict[str, Any]:
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
                return {}
            parsed_mapping = _coerce_mapping_like(parsed)
            if parsed_mapping is not None:
                return parsed_mapping

        result: Dict[str, Any] = {}
        for name in (
            "stance",
            "confidence",
            "reasoning",
            "red_line_triggered",
            "red_line",
        ):
            if hasattr(value, name):
                result[name] = getattr(value, name)
        return result

    @staticmethod
    def _normalize_mode(mode: Any, *, warnings: List[str]) -> str:
        raw = _normalize_text(mode).lower()
        if not raw:
            return "meeting"
        normalized = _MODE_ALIASES.get(raw, raw)
        if normalized in _VALID_MODES:
            if normalized != raw:
                warnings.append(f"Mode alias '{raw}' normalized to '{normalized}'.")
            return normalized
        warnings.append(f"Unsupported prime decision mode '{raw}' normalized to 'meeting'.")
        return "meeting"

    @staticmethod
    def _normalize_minister_stance(stance: str) -> str:
        if stance in {"support", "oppose", "neutral"}:
            return stance
        support_aliases = {
            "accept",
            "accept_with_mitigation",
            "support_with_caution",
            "proceed",
            "yes",
        }
        oppose_aliases = {
            "reject",
            "block",
            "no",
        }
        if stance in support_aliases:
            return "support"
        if stance in oppose_aliases:
            return "oppose"
        return "neutral"

    @staticmethod
    def _normalize_confidence_value(
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
    ) -> float:
        try:
            numeric = float(value if value is not None else 0.0)
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
    def _normalize_final_decision(
        decision: Mapping[str, Any] | Dict[str, Any],
        *,
        council_payload: Mapping[str, Any],
        mode: str,
        warnings: List[str],
    ) -> Dict[str, Any]:
        payload = dict(decision or {})
        outcome_raw = str(payload.get("final_outcome", "defer")).strip().lower()
        if not outcome_raw:
            outcome_raw = "defer"
        allowed_outcomes = {
            "accept",
            "accept_with_mitigation",
            "defer",
            "reject",
            "direct_response",
        }
        if outcome_raw not in allowed_outcomes:
            warnings.append(f"Unsupported final_outcome '{outcome_raw}' normalized to 'defer'.")
            outcome_raw = "defer"

        reason = str(payload.get("reason", "")).strip()
        if not reason:
            reason = "prime_decision_reason_unavailable"
            warnings.append("Missing final decision reason normalized to placeholder.")

        normalized = dict(payload)
        normalized["final_outcome"] = outcome_raw
        normalized["reason"] = reason
        normalized["mode"] = mode
        normalized.setdefault("council_outcome", str(council_payload.get("outcome", "")))
        normalized.setdefault(
            "council_recommendation", str(council_payload.get("recommendation", ""))
        )
        return normalized

    @staticmethod
    def _normalize_context_keys(
        context: Optional[Mapping[str, Any]],
        warnings: List[str],
    ) -> List[str]:
        if context is None:
            return []
        if not isinstance(context, Mapping):
            warnings.append("Invalid context payload ignored for decision metadata.")
            return []

        keys: List[str] = []
        for key in context.keys():
            text = _normalize_text(key)
            if not text:
                continue
            keys.append(text)
        return sorted(set(keys))

    @staticmethod
    def _normalize_string_list(
        value: Any,
        *,
        warnings: List[str],
        field_name: str,
        lowercase: bool,
    ) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            raw = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [_normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    f"{field_name} iterable iteration failed; partial values preserved."
                )
        elif isinstance(value, Mapping):
            warnings.append(f"Invalid {field_name} payload normalized to empty list.")
            return []
        elif isinstance(value, Iterable):
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            raw = [_normalize_text(item) for item in raw_items]
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

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
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
