"""Orchestrator plugin for council output normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from core.contracts import (
    CouncilNormalizationContract,
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import CouncilNormalizationEngine


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
        key = CouncilNormalizationModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class CouncilNormalizationModule(ModulePlugin):
    """Pipeline module that normalizes council outputs for prime handoff."""

    engine: CouncilNormalizationEngine

    @classmethod
    def create(cls) -> "CouncilNormalizationModule":
        return cls(engine=CouncilNormalizationEngine())

    def name(self) -> str:
        return "council_normalization"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "normalizes_council_result": True,
            "normalizes_minister_outputs": True,
            "emits_council_normalization_contract": True,
            "supports_contract_or_result_input": True,
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
        has_council_result = self._read_normalized_key(context.state, ("council_result",)) is not None
        has_council_contract = self._read_normalized_key(context.state, ("council_contract",)) is not None
        if not has_council_result and not has_council_contract:
            raise ValueError(
                "CouncilNormalizationModule requires 'council_result' or 'council_contract'."
            )

    def execute(self, context: ExecutionContext) -> ModuleResult:
        mode = self._resolve_mode(context)
        council_payload, payload_source = self._resolve_council_payload(context)

        try:
            normalized_raw = self.engine.normalize(
                council_result=council_payload,
                mode=mode,
            )
            normalized = self._normalize_engine_result(
                normalized_raw,
                fallback_mode=mode,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            message = f"{type(exc).__name__}: {exc}"
            fallback_contract = CouncilNormalizationContract(
                mode=str(mode).strip().lower() or "meeting",
                outcome="deadlocked",
                recommendation="defer",
                consensus_strength=0.0,
                minister_count=0,
                failed_minister_count=0,
                red_line_count=0,
                council_invoked=False,
                warning_count=1,
                source="council_normalization",
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "council_result_normalized": {
                        "outcome": "deadlocked",
                        "recommendation": "defer",
                        "avg_confidence": 0.0,
                        "consensus_strength": 0.0,
                        "reasoning": "Council normalization failed.",
                        "mode": fallback_contract.mode,
                        "red_line_concerns": [],
                        "minister_outputs": {},
                        "minister_positions": {},
                        "council_positions": [],
                        "ministers_failed": [],
                        "source_outcome": "",
                        "source_recommendation": "",
                    },
                    "minister_outputs_normalized": {},
                    "council_positions_normalized": [],
                    "council_normalization_contract": fallback_contract,
                    "council_normalization_warnings": [message],
                    "council_normalization_source": payload_source,
                },
                metrics={
                    "council_normalization_warning_count": 1,
                    "council_normalization_minister_count": 0,
                    "council_normalization_failed_minister_count": 0,
                },
                errors=[message],
            )

        status = ModuleStatus.SUCCESS if not normalized["warnings"] else ModuleStatus.DEGRADED
        return ModuleResult(
            status=status,
            outputs={
                "council_result_normalized": self._coerce_mapping(normalized["normalized_council"]) or {},
                "minister_outputs_normalized": self._coerce_mapping(normalized["normalized_minister_outputs"]) or {},
                "council_positions_normalized": self._coerce_positions(normalized["council_positions"]),
                "council_normalization_contract": normalized["contract"],
                "council_normalization_warnings": self._coerce_string_list(normalized["warnings"]),
                "council_normalization_source": payload_source,
            },
            metrics={
                "council_normalization_warning_count": len(normalized["warnings"]),
                "council_normalization_minister_count": normalized["contract"].minister_count,
                "council_normalization_failed_minister_count": normalized["contract"].failed_minister_count,
            },
            errors=self._coerce_string_list(normalized["warnings"]),
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True)

    @staticmethod
    def _resolve_mode(context: ExecutionContext) -> str:
        council_result_raw = CouncilNormalizationModule._read_normalized_key(
            context.state,
            ("council_result",),
        )
        council_result = _coerce_mapping(council_result_raw) or {}
        candidates = (
            CouncilNormalizationModule._read_normalized_key(context.state, ("resolved_mode", "mode")),
            CouncilNormalizationModule._read_normalized_key(context.state, ("requested_mode", "mode")),
            CouncilNormalizationModule._read_normalized_key(context.metadata, ("requested_mode", "mode")),
            CouncilNormalizationModule._read_normalized_key(
                context.input_contract.metadata,
                ("requested_mode", "mode"),
            ),
            CouncilNormalizationModule._read_normalized_key(context.config, ("requested_mode", "mode")),
            CouncilNormalizationModule._read_normalized_key(council_result, ("mode",)),
            "meeting",
        )
        for candidate in candidates:
            text = CouncilNormalizationModule._normalize_text(candidate).lower()
            if text:
                return text
        return "meeting"

    @staticmethod
    def _resolve_council_payload(context: ExecutionContext) -> Tuple[Any, str]:
        council_result = CouncilNormalizationModule._read_normalized_key(
            context.state,
            ("council_result",),
        )
        if council_result is not None:
            return council_result, "state.council_result"
        return CouncilNormalizationModule._read_normalized_key(
            context.state,
            ("council_contract",),
        ), "state.council_contract"

    @classmethod
    def _normalize_engine_result(
        cls,
        value: Any,
        *,
        fallback_mode: Any,
    ) -> Dict[str, Any]:
        warnings: list[str] = []
        payload_mapping = _coerce_mapping(value)
        payload = payload_mapping or {}
        if payload_mapping is None and value not in (None, "", {}):
            warnings.append("Council normalization engine returned non-mapping result; normalized.")

        normalized_council_raw = cls._read_field(value, payload, "normalized_council")
        minister_outputs_raw = cls._read_field(value, payload, "normalized_minister_outputs")
        positions_raw = cls._read_field(value, payload, "council_positions")
        contract_raw = cls._read_field(value, payload, "contract")
        warnings_raw = cls._read_field(value, payload, "warnings")

        normalized_minister_outputs = cls._normalize_minister_outputs(
            minister_outputs_raw,
            warnings=warnings,
        )

        normalized_council = cls._normalize_council_payload(
            normalized_council_raw,
            fallback_mode=fallback_mode,
            normalized_minister_outputs=normalized_minister_outputs,
            warnings=warnings,
        )
        if not normalized_minister_outputs:
            normalized_minister_outputs = dict(
                cls._normalize_minister_outputs(
                    normalized_council.get("minister_outputs"),
                    warnings=warnings,
                )
            )

        council_positions = cls._normalize_positions(
            positions_raw,
            normalized_minister_outputs=normalized_minister_outputs,
            warnings=warnings,
        )

        warnings_list = cls._dedupe_strings(cls._coerce_string_list(warnings_raw) + warnings)

        contract = cls._normalize_contract(
            contract_raw,
            normalized_council=normalized_council,
            normalized_minister_outputs=normalized_minister_outputs,
            warnings=warnings_list,
        )

        normalized_council["minister_outputs"] = dict(normalized_minister_outputs)
        normalized_council["minister_positions"] = dict(normalized_minister_outputs)
        normalized_council["council_positions"] = list(council_positions)

        return {
            "normalized_council": normalized_council,
            "normalized_minister_outputs": normalized_minister_outputs,
            "council_positions": council_positions,
            "contract": contract,
            "warnings": warnings_list,
        }

    @staticmethod
    def _read_field(value: Any, payload: Mapping[str, Any], field: str) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = CouncilNormalizationModule._normalize_key_name(field)
        normalized_payload = _coerce_mapping(payload) or {}
        for raw_key, raw_value in normalized_payload.items():
            if CouncilNormalizationModule._normalize_key_name(raw_key) == normalized_field:
                return raw_value
        if hasattr(value, field):
            return getattr(value, field)
        return None

    @classmethod
    def _normalize_council_payload(
        cls,
        value: Any,
        *,
        fallback_mode: Any,
        normalized_minister_outputs: Mapping[str, Mapping[str, Any]],
        warnings: list[str],
    ) -> Dict[str, Any]:
        raw_mapping = _coerce_mapping(value)
        raw = raw_mapping or {}
        if raw_mapping is None and value not in (None, "", {}):
            warnings.append("Normalized council payload was invalid and normalized to empty mapping.")

        outcome = cls._normalize_text(raw.get("outcome", "deadlocked")).lower() or "deadlocked"
        recommendation = cls._normalize_text(raw.get("recommendation", "defer")).lower() or "defer"
        mode = cls._normalize_text(raw.get("mode") or fallback_mode or "meeting").lower() or "meeting"
        consensus_strength = cls._safe_confidence(
            raw.get("consensus_strength", raw.get("avg_confidence", 0.0))
        )
        reasoning = str(raw.get("reasoning", "") or "")
        red_line_concerns = cls._coerce_string_list(raw.get("red_line_concerns"), lowercase=True)
        ministers_failed = cls._coerce_string_list(raw.get("ministers_failed"))

        source_outcome = cls._normalize_text(raw.get("source_outcome", raw.get("outcome", ""))).lower()
        source_recommendation = cls._normalize_text(
            raw.get("source_recommendation", raw.get("recommendation", ""))
        ).lower()

        return {
            "outcome": outcome,
            "recommendation": recommendation,
            "avg_confidence": consensus_strength,
            "consensus_strength": consensus_strength,
            "reasoning": reasoning,
            "mode": mode,
            "red_line_concerns": red_line_concerns,
            "minister_outputs": dict(normalized_minister_outputs),
            "minister_positions": dict(normalized_minister_outputs),
            "council_positions": [],
            "ministers_failed": ministers_failed,
            "source_outcome": source_outcome,
            "source_recommendation": source_recommendation,
        }

    @classmethod
    def _normalize_minister_outputs(
        cls,
        value: Any,
        *,
        warnings: list[str],
    ) -> Dict[str, Dict[str, Any]]:
        if isinstance(value, Mapping):
            candidates = _coerce_mapping(value) or {}
        elif isinstance(value, (bytes, bytearray)):
            candidates = {}
            if value:
                warnings.append("Minister outputs payload was invalid and normalized to empty mapping.")
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            mapping_like = _coerce_mapping(value)
            if mapping_like is not None:
                candidates = mapping_like
            else:
                candidates = {
                    cls._normalize_text(item.get("minister", "")).lower(): item
                    for item in (_coerce_iterable_items(value, preserve_partial=True)[0])
                    if isinstance(item, Mapping) and cls._normalize_text(item.get("minister", ""))
                }
                if value and not candidates:
                    warnings.append("Council positions payload was invalid and normalized to empty mapping.")
        elif isinstance(value, Iterable):
            seq, _ = _coerce_iterable_items(value, preserve_partial=True)
            mapping_like = _coerce_mapping(seq)
            if mapping_like is not None:
                candidates = mapping_like
            else:
                candidates = {
                    cls._normalize_text(item.get("minister", "")).lower(): item
                    for item in seq
                    if isinstance(item, Mapping) and cls._normalize_text(item.get("minister", ""))
                }
                if seq and not candidates:
                    warnings.append("Council positions payload was invalid and normalized to empty mapping.")
        else:
            candidates = {}
            if value not in (None, "", {}):
                warnings.append("Minister outputs payload was invalid and normalized to empty mapping.")

        normalized: Dict[str, Dict[str, Any]] = {}
        for key, raw_item in candidates.items():
            name = cls._normalize_text(key).lower()
            if not name:
                continue
            payload_mapping = _coerce_mapping(raw_item)
            payload = payload_mapping or {}
            if payload_mapping is None:
                warnings.append(f"Minister payload for '{name}' normalized from non-mapping value.")

            stance = cls._normalize_text(payload.get("stance", "neutral")).lower() or "neutral"
            if stance not in {"support", "oppose", "neutral"}:
                stance = "neutral"

            normalized[name] = {
                "stance": stance,
                "confidence": cls._safe_confidence(payload.get("confidence", 0.0)),
                "reasoning": cls._normalize_text(payload.get("reasoning", "")),
                "red_line_triggered": bool(
                    cls._to_bool(
                        payload.get(
                            "red_line_triggered",
                            payload.get("red_line", False),
                        )
                    )
                ),
            }
        return normalized

    @classmethod
    def _normalize_positions(
        cls,
        value: Any,
        *,
        normalized_minister_outputs: Mapping[str, Mapping[str, Any]],
        warnings: list[str],
    ) -> list[Dict[str, Any]]:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            positions: list[Dict[str, Any]] = []
            raw_items, _ = _coerce_iterable_items(value, preserve_partial=True)
            for item in raw_items:
                if not isinstance(item, Mapping):
                    continue
                minister = cls._normalize_text(item.get("minister", "")).lower()
                if not minister:
                    continue
                positions.append(
                    {
                        "minister": minister,
                        "stance": cls._normalize_text(item.get("stance", "neutral")).lower() or "neutral",
                        "confidence": cls._safe_confidence(item.get("confidence", 0.0)),
                        "reasoning": cls._normalize_text(item.get("reasoning", "")),
                        "red_line_triggered": bool(
                            cls._to_bool(
                                item.get(
                                    "red_line_triggered",
                                    item.get("red_line", False),
                                )
                            )
                        ),
                    }
                )
            if positions:
                return positions
            if value:
                warnings.append("Council positions list was invalid and rebuilt from minister outputs.")
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, Mapping)):
            seq, _ = _coerce_iterable_items(value, preserve_partial=True)
            positions: list[Dict[str, Any]] = []
            for item in seq:
                if not isinstance(item, Mapping):
                    continue
                minister = cls._normalize_text(item.get("minister", "")).lower()
                if not minister:
                    continue
                positions.append(
                    {
                        "minister": minister,
                        "stance": cls._normalize_text(item.get("stance", "neutral")).lower() or "neutral",
                        "confidence": cls._safe_confidence(item.get("confidence", 0.0)),
                        "reasoning": cls._normalize_text(item.get("reasoning", "")),
                        "red_line_triggered": bool(
                            cls._to_bool(
                                item.get(
                                    "red_line_triggered",
                                    item.get("red_line", False),
                                )
                            )
                        ),
                    }
                )
            if positions:
                return positions
            if seq:
                warnings.append("Council positions list was invalid and rebuilt from minister outputs.")
        elif value not in (None, "", []):
            warnings.append("Council positions payload was invalid and rebuilt from minister outputs.")

        return [
            {
                "minister": name,
                "stance": details.get("stance", "neutral"),
                "confidence": details.get("confidence", 0.0),
                "reasoning": details.get("reasoning", ""),
                "red_line_triggered": bool(details.get("red_line_triggered", False)),
            }
            for name, details in normalized_minister_outputs.items()
        ]

    @classmethod
    def _normalize_contract(
        cls,
        value: Any,
        *,
        normalized_council: Mapping[str, Any],
        normalized_minister_outputs: Mapping[str, Mapping[str, Any]],
        warnings: list[str],
    ) -> CouncilNormalizationContract:
        if isinstance(value, CouncilNormalizationContract):
            return value

        source_outcome = str(normalized_council.get("source_outcome", "")).strip().lower()
        council_invoked = source_outcome not in {
            "quick_mode_direct_response",
            "council_disabled_ablation",
            "not_invoked",
            "direct_response",
        }
        return CouncilNormalizationContract(
            mode=str(normalized_council.get("mode", "meeting") or "meeting").strip().lower() or "meeting",
            outcome=str(normalized_council.get("outcome", "deadlocked") or "deadlocked").strip().lower()
            or "deadlocked",
            recommendation=str(
                normalized_council.get("recommendation", "defer") or "defer"
            ).strip().lower()
            or "defer",
            consensus_strength=cls._safe_confidence(
                normalized_council.get("consensus_strength", 0.0)
            ),
            minister_count=len(normalized_minister_outputs),
            failed_minister_count=len(cls._coerce_string_list(normalized_council.get("ministers_failed"))),
            red_line_count=len(
                cls._coerce_string_list(
                    normalized_council.get("red_line_concerns"),
                    lowercase=True,
                )
            ),
            council_invoked=council_invoked,
            warning_count=len(warnings),
            source="council_normalization",
        )

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
    def _coerce_string_list(value: Any, *, lowercase: bool = False) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [bytes(value).decode("utf-8", errors="replace").strip()]
        elif isinstance(value, str):
            raw_items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [CouncilNormalizationModule._normalize_text(item) for item in items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [CouncilNormalizationModule._normalize_text(item) for item in items]
        else:
            raw_items = [CouncilNormalizationModule._normalize_text(value)]

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
    def _dedupe_strings(items: Sequence[str]) -> list[str]:
        deduped: list[str] = []
        seen = set()
        for item in items:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)
        return deduped

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = CouncilNormalizationModule._normalize_text(value).lower()
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
            CouncilNormalizationModule._normalize_text(value)
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
        normalized_keys = {CouncilNormalizationModule._normalize_key_name(key) for key in keys}
        payload = _coerce_mapping(source)
        if payload is None:
            return None
        for raw_key, value in payload.items():
            if CouncilNormalizationModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None

    @staticmethod
    def _coerce_mapping(value: Any) -> Dict[str, Any] | None:
        return _coerce_mapping(value)

    @staticmethod
    def _coerce_positions(value: Any) -> list[Dict[str, Any]]:
        if isinstance(value, Mapping):
            return []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            return [item for item in items if isinstance(item, Mapping)]
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            return [item for item in items if isinstance(item, Mapping)]
        return []
