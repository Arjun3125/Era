"""Orchestrator plugin wrapper around the council execution engine."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from core.contracts import (
    CouncilContract,
    ExecutionContext,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import CouncilExecutionEngine


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
        key = CouncilExecutionModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class CouncilExecutionModule(ModulePlugin):
    """Pipeline module that runs mode-aware council deliberation."""

    engine: CouncilExecutionEngine

    @classmethod
    def create(cls, *, llm: Any = None) -> "CouncilExecutionModule":
        return cls(engine=CouncilExecutionEngine.create(llm=llm))

    def name(self) -> str:
        return "council_execution"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "mode_aware_execution": True,
            "supports_minister_selection": True,
            "supports_ablation_flags": True,
            "normalizes_minister_aliases": True,
            "emits_council_warnings": True,
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
        if not isinstance(context.input_contract.user_input, str):
            raise TypeError("InputContract.user_input must be a string.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        mode = self._resolve_mode(context)
        routing_context, routing_sources = self._merge_routing_context(context)
        selected_ministers = self._resolve_selected_ministers(context)

        try:
            council_result_raw = self.engine.convene(
                mode=mode,
                user_input=context.input_contract.user_input,
                context=routing_context,
                selected_ministers=selected_ministers,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            message = f"{type(exc).__name__}: {exc}"
            fallback_contract = CouncilContract(
                outcome="engine_error",
                recommendation="defer",
                consensus_strength=0.0,
                minister_positions={},
                red_line_concerns=[],
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "council_result": {
                        "outcome": "engine_error",
                        "recommendation": "defer",
                        "mode": str(mode).strip().lower() or "meeting",
                        "ministers_involved": [],
                        "ministers_failed": [],
                        "minister_positions": {},
                        "minister_outputs": {},
                        "council_positions": [],
                        "reasoning": "Council execution failed before deliberation.",
                        "consensus_strength": 0.0,
                        "red_line_concerns": [],
                        "total_ministers_consulted": 0,
                        "support_count": 0,
                        "oppose_count": 0,
                        "neutral_count": 0,
                        "warnings": [message],
                        "warning_count": 1,
                    },
                    "council_contract": fallback_contract,
                    "council_warnings": [message],
                    "council_execution_sources": list(routing_sources),
                },
                metrics={
                    "ministers_consulted": 0,
                    "ministers_failed": 0,
                    "council_warning_count": 1,
                    "council_source_count": len(routing_sources),
                },
                errors=[message],
            )

        council_result = self._normalize_council_result(
            council_result_raw,
            fallback_mode=mode,
        )
        consensus_strength = self._safe_confidence(
            council_result.get("consensus_strength", 0.0)
        )
        council_contract = CouncilContract(
            outcome=str(council_result.get("outcome", "not_invoked")).strip().lower() or "not_invoked",
            recommendation=str(council_result.get("recommendation", "defer")).strip().lower() or "defer",
            consensus_strength=consensus_strength,
            minister_positions=_coerce_mapping(council_result.get("minister_positions", {}) or {}) or {},
            red_line_concerns=self._coerce_string_list(council_result.get("red_line_concerns", []) or []),
        )

        failed = self._coerce_string_list(council_result.get("ministers_failed"))
        warnings = self._coerce_string_list(council_result.get("warnings"))
        status = ModuleStatus.DEGRADED if (failed or warnings) else ModuleStatus.SUCCESS

        return ModuleResult(
            status=status,
            outputs={
                "council_result": council_result,
                "council_contract": council_contract,
                "council_warnings": warnings,
                "council_execution_sources": list(routing_sources),
            },
            metrics={
                "ministers_consulted": int(
                    council_result.get("total_ministers_consulted", 0) or 0
                ),
                "ministers_failed": len(failed),
                "council_warning_count": len(warnings),
                "council_source_count": len(routing_sources),
            },
            errors=self._dedupe_strings(failed + warnings),
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(
            ok=True,
            details={
                "mode": self.engine.get_current_mode(),
                "disabled": self.engine.disabled,
            },
        )

    @staticmethod
    def _resolve_mode(context: ExecutionContext) -> str:
        routing_context_raw = CouncilExecutionModule._read_normalized_key(
            context.state,
            ("routing_context",),
        )
        routing_context = _coerce_mapping(routing_context_raw) or {}
        candidates = (
            CouncilExecutionModule._read_normalized_key(context.state, ("resolved_mode", "mode")),
            CouncilExecutionModule._read_normalized_key(context.state, ("requested_mode", "mode")),
            CouncilExecutionModule._read_normalized_key(context.metadata, ("requested_mode", "mode")),
            CouncilExecutionModule._read_normalized_key(
                context.input_contract.metadata,
                ("requested_mode", "mode"),
            ),
            CouncilExecutionModule._read_normalized_key(context.config, ("requested_mode", "mode")),
            CouncilExecutionModule._read_normalized_key(routing_context, ("requested_mode", "mode")),
            "meeting",
        )
        for candidate in candidates:
            text = CouncilExecutionModule._normalize_text(candidate).lower()
            if text:
                return text
        return "meeting"

    @staticmethod
    def _resolve_selected_ministers(context: ExecutionContext) -> Any:
        routing_context_raw = CouncilExecutionModule._read_normalized_key(
            context.state,
            ("routing_context",),
        )
        routing_context = _coerce_mapping(routing_context_raw) or {}
        candidates = (
            CouncilExecutionModule._read_normalized_key(context.state, ("selected_ministers",)),
            CouncilExecutionModule._read_normalized_key(context.metadata, ("selected_ministers",)),
            CouncilExecutionModule._read_normalized_key(
                context.input_contract.metadata,
                ("selected_ministers",),
            ),
            CouncilExecutionModule._read_normalized_key(context.config, ("selected_ministers",)),
            CouncilExecutionModule._read_normalized_key(routing_context, ("selected_ministers",)),
        )
        for candidate in candidates:
            if candidate is None:
                continue
            return candidate
        return None

    @staticmethod
    def _merge_routing_context(context: ExecutionContext) -> Tuple[Dict[str, Any], list[str]]:
        merged: Dict[str, Any] = {}
        sources: list[str] = []
        routing_keys = ("routing_context",)
        for source_name, payload in (
            (
                "context.config.routing_context",
                CouncilExecutionModule._read_normalized_key(context.config, routing_keys),
            ),
            (
                "input.metadata.routing_context",
                CouncilExecutionModule._read_normalized_key(
                    context.input_contract.metadata,
                    routing_keys,
                ),
            ),
            (
                "run.metadata.routing_context",
                CouncilExecutionModule._read_normalized_key(context.metadata, routing_keys),
            ),
            (
                "state.routing_context",
                CouncilExecutionModule._read_normalized_key(context.state, routing_keys),
            ),
        ):
            payload_mapping = _coerce_mapping(payload)
            if payload_mapping is None:
                continue
            merged.update(payload_mapping)
            sources.append(source_name)

        deduped_sources: list[str] = []
        seen = set()
        for source in sources:
            if source in seen:
                continue
            seen.add(source)
            deduped_sources.append(source)
        return merged, deduped_sources

    @staticmethod
    def _safe_confidence(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if not (numeric == numeric) or numeric == float("inf") or numeric == float("-inf"):
            return 0.0
        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    @classmethod
    def _normalize_council_result(
        cls,
        payload: Any,
        *,
        fallback_mode: Any,
    ) -> Dict[str, Any]:
        warnings: list[str] = []
        payload_mapping = _coerce_mapping(payload)
        raw = payload_mapping or {}
        if payload_mapping is None:
            warnings.append("Council execution engine returned non-mapping result; normalized.")

        mode = cls._normalize_mode_candidate(cls._read_field(raw, "mode"))
        if not mode:
            mode = cls._normalize_mode_candidate(fallback_mode) or "meeting"

        minister_outputs = cls._normalize_minister_outputs(
            cls._read_field(raw, "minister_positions", fallback=cls._read_field(raw, "minister_outputs")),
            warnings=warnings,
        )
        ministers_involved = cls._coerce_string_list(
            cls._read_field(raw, "ministers_involved"),
            lowercase=True,
        )
        if not ministers_involved:
            ministers_involved = list(minister_outputs.keys())

        failed = cls._coerce_string_list(cls._read_field(raw, "ministers_failed"))
        red_lines = cls._coerce_string_list(
            cls._read_field(raw, "red_line_concerns"),
            lowercase=True,
        )
        reasoning = cls._normalize_text(cls._read_field(raw, "reasoning"))

        support_count = cls._safe_int(cls._read_field(raw, "support_count"), default=0)
        oppose_count = cls._safe_int(cls._read_field(raw, "oppose_count"), default=0)
        neutral_count = cls._safe_int(cls._read_field(raw, "neutral_count"), default=0)
        if support_count + oppose_count + neutral_count == 0 and minister_outputs:
            support_count = sum(
                1
                for payload_item in minister_outputs.values()
                if str(payload_item.get("stance", "")).strip().lower() == "support"
            )
            oppose_count = sum(
                1
                for payload_item in minister_outputs.values()
                if str(payload_item.get("stance", "")).strip().lower() == "oppose"
            )
            neutral_count = max(len(minister_outputs) - support_count - oppose_count, 0)

        total_consulted = cls._safe_int(
            cls._read_field(raw, "total_ministers_consulted"),
            default=len(minister_outputs),
        )
        if total_consulted <= 0 and minister_outputs:
            total_consulted = len(minister_outputs)

        engine_warnings = cls._coerce_string_list(cls._read_field(raw, "warnings"))
        warnings = cls._dedupe_strings(engine_warnings + warnings)

        council_positions = [
            {
                "minister": name,
                "stance": payload_item.get("stance"),
                "confidence": payload_item.get("confidence"),
                "reasoning": payload_item.get("reasoning", ""),
                "red_line_triggered": bool(payload_item.get("red_line_triggered", False)),
            }
            for name, payload_item in minister_outputs.items()
        ]

        return {
            "outcome": cls._normalize_mode_candidate(cls._read_field(raw, "outcome")) or "not_invoked",
            "recommendation": cls._normalize_mode_candidate(cls._read_field(raw, "recommendation")) or "defer",
            "mode": mode,
            "ministers_involved": ministers_involved,
            "ministers_failed": failed,
            "minister_positions": minister_outputs,
            "minister_outputs": dict(minister_outputs),
            "council_positions": council_positions,
            "reasoning": reasoning,
            "consensus_strength": cls._safe_confidence(cls._read_field(raw, "consensus_strength")),
            "red_line_concerns": red_lines,
            "total_ministers_consulted": total_consulted,
            "support_count": support_count,
            "oppose_count": oppose_count,
            "neutral_count": neutral_count,
            "warnings": warnings,
            "warning_count": len(warnings),
        }

    @staticmethod
    def _read_field(payload: Mapping[str, Any], field: str, *, fallback: Any = None) -> Any:
        if field in payload:
            return payload.get(field)
        normalized_field = CouncilExecutionModule._normalize_key_name(field)
        normalized_payload = _coerce_mapping(payload) or {}
        for raw_key, value in normalized_payload.items():
            if CouncilExecutionModule._normalize_key_name(raw_key) == normalized_field:
                return value
        return fallback

    @classmethod
    def _normalize_minister_outputs(
        cls,
        value: Any,
        *,
        warnings: list[str],
    ) -> Dict[str, Dict[str, Any]]:
        if isinstance(value, Mapping):
            candidates = _coerce_mapping(value) or {}
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            mapping_like = _coerce_mapping(value)
            if mapping_like is not None:
                candidates = mapping_like
            else:
                candidates = {
                    str(item.get("minister", "")).strip().lower(): item
                    for item in (_coerce_iterable_items(value, preserve_partial=True)[0])
                    if isinstance(item, Mapping) and str(item.get("minister", "")).strip()
                }
                if value and not candidates:
                    warnings.append("Council positions payload was invalid and normalized to empty mapping.")
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            seq, _ = _coerce_iterable_items(value, preserve_partial=True)
            mapping_like = _coerce_mapping(seq)
            if mapping_like is not None:
                candidates = mapping_like
            else:
                candidates = {
                    str(item.get("minister", "")).strip().lower(): item
                    for item in seq
                    if isinstance(item, Mapping) and str(item.get("minister", "")).strip()
                }
                if seq and not candidates:
                    warnings.append("Council positions payload was invalid and normalized to empty mapping.")
        else:
            candidates = {}
            if value not in (None, "", {}):
                warnings.append("Minister outputs payload was invalid and normalized to empty mapping.")

        normalized: Dict[str, Dict[str, Any]] = {}
        seen = set()
        for key, raw_item in candidates.items():
            name = str(key).strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)

            payload_mapping = _coerce_mapping(raw_item)
            payload = payload_mapping or {}
            if payload_mapping is None:
                warnings.append(f"Minister payload for '{name}' normalized from non-mapping value.")

            stance = str(payload.get("stance", "neutral")).strip().lower() or "neutral"
            if stance not in {"support", "oppose", "neutral"}:
                stance = "neutral"
            confidence = cls._safe_confidence(payload.get("confidence", 0.0))
            reasoning = str(payload.get("reasoning", "") or "")
            red_line = cls._to_bool(
                payload.get("red_line_triggered", payload.get("red_line", False))
            )

            normalized[name] = {
                "stance": stance,
                "confidence": confidence,
                "reasoning": reasoning,
                "red_line_triggered": bool(red_line),
            }
        return normalized

    @staticmethod
    def _normalize_mode_candidate(value: Any) -> str:
        text = CouncilExecutionModule._normalize_text(value).lower()
        return text or ""

    @staticmethod
    def _safe_int(value: Any, *, default: int, minimum: int = 0) -> int:
        try:
            numeric = int(value)
        except Exception:
            numeric = default
        if numeric < minimum:
            return minimum
        return numeric

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = CouncilExecutionModule._normalize_text(value).lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return None

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
            raw_items = [CouncilExecutionModule._normalize_text(item) for item in items]
        elif isinstance(value, Mapping):
            return []
        elif isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [CouncilExecutionModule._normalize_text(item) for item in items]
        else:
            raw_items = [CouncilExecutionModule._normalize_text(value)]

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            CouncilExecutionModule._normalize_text(value)
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
        normalized_keys = {CouncilExecutionModule._normalize_key_name(key) for key in keys}
        payload = _coerce_mapping(source)
        if payload is None:
            return None
        for raw_key, value in payload.items():
            if CouncilExecutionModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None
