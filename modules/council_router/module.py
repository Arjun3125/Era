"""Module-plugin wrapper around mode routing decisions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Tuple
from pathlib import Path

from core.contracts import (
    ExecutionContext,
    ModeResolutionContract,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
)

from .engine import ModeRoutingEngine
from .mode_orchestrator import ExecutionConfig, ModeOrchestrator
from modules.expert_router import ExpertRouterPredictor
from modules.council_learning import CouncilWeightPredictor


def _coerce_iterable_items(
    value: Any,
    *,
    preserve_partial: bool,
) -> tuple[list[Any], bool]:
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
        items, failed = _coerce_iterable_items(value.items(), preserve_partial=True)
        if failed and not items:
            return {}
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
        if failed and not raw_items:
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
        key = ModeRoutingModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class ModeRoutingModule(ModulePlugin):
    """Orchestrator-compatible module that resolves mode routing plans."""

    orchestrator: ModeOrchestrator
    engine: ModeRoutingEngine

    @classmethod
    def create(cls, config: ExecutionConfig | None = None) -> "ModeRoutingModule":
        """Convenience constructor with default mode orchestrator."""
        orchestrator = ModeOrchestrator(config=config)
        return cls(
            orchestrator=orchestrator,
            engine=ModeRoutingEngine(orchestrator=orchestrator),
        )

    def name(self) -> str:
        return "mode_routing"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "resolves_mode": True,
            "supports_uncertainty_control": True,
            "supports_ablation_flags": True,
            "normalizes_mode_aliases": True,
            "emits_mode_routing_warnings": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context.state, Mapping):
            raise TypeError("ExecutionContext.state must be a mapping.")
        if not isinstance(context.config, Mapping):
            raise TypeError("ExecutionContext.config must be a mapping.")
        if not isinstance(context.metadata, Mapping):
            raise TypeError("ExecutionContext.metadata must be a mapping.")
        if not isinstance(context.input_contract.metadata, Mapping):
            raise TypeError("InputContract.metadata must be a mapping.")
        if not isinstance(context.input_contract.user_input, str):
            raise TypeError("InputContract.user_input must be a string.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        routing_context, routing_sources = self._merge_routing_context(context)
        requested_mode_raw = self._resolve_requested_mode(context, routing_context)
        user_input = context.input_contract.user_input

        try:
            result = self.engine.route(
                requested_mode=requested_mode_raw,
                user_input=user_input,
                routing_context=routing_context,
            )
            selected_ministers = self._to_string_list(result.selected_ministers, lowercase=True)
            expert_weights = {}
            if result.should_invoke_council:
                expert_weights = self._apply_weight_model(
                    context=context,
                    routing_context=routing_context,
                    user_input=user_input,
                )
                if not expert_weights:
                    expert_weights = self._apply_expert_router(
                        context=context,
                        routing_context=routing_context,
                        user_input=user_input,
                        selected_ministers=selected_ministers,
                    )
            if expert_weights:
                selected_ministers = list(expert_weights.keys())
            execution_plan = self._normalize_execution_plan(
                result.execution_plan,
                defaults=self._execution_plan_defaults(),
            )
            warnings = self._to_string_list(result.warnings)
            uncertainty_policy = _coerce_mapping(result.uncertainty_policy) or {}
            routing_metadata = _coerce_mapping(result.routing_metadata) or {}
            routing_sources = self._to_string_list(routing_sources)

            status = ModuleStatus.SUCCESS if not warnings else ModuleStatus.DEGRADED
            return ModuleResult(
                status=status,
                outputs={
                    "resolved_mode": result.resolved_mode,
                    "should_invoke_council": result.should_invoke_council,
                    "selected_ministers": selected_ministers,
                    "expert_weights": expert_weights,
                    "mode_frame": result.frame,
                    "execution_plan": execution_plan,
                    "mode_contract": result.mode_contract,
                    "mode_routing_warnings": warnings,
                    "mode_uncertainty_policy": uncertainty_policy,
                    "mode_routing_metadata": routing_metadata,
                    "mode_routing_sources": routing_sources,
                },
                metrics={
                    "minister_count": len(selected_ministers),
                    "mode_warning_count": len(warnings),
                    "mode_uncertainty_applied": bool(uncertainty_policy.get("applied")),
                    "mode_routing_source_count": len(routing_sources),
                },
                errors=warnings,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            message = f"{type(exc).__name__}: {exc}"
            fallback_mode = str(requested_mode_raw or "meeting").strip().lower() or "meeting"
            execution_plan = self._safe_execution_plan(fallback_mode)
            mode_contract = ModeResolutionContract(
                mode=fallback_mode,
                should_invoke_council=bool(execution_plan.get("use_dynamic_council", False)),
                selected_ministers=[],
                rationale="mode_routing_module_error",
                confidence=0.0,
            )
            return ModuleResult(
                status=ModuleStatus.DEGRADED,
                outputs={
                    "resolved_mode": fallback_mode,
                    "should_invoke_council": mode_contract.should_invoke_council,
                    "selected_ministers": [],
                    "mode_frame": "Mode routing failed before framing.",
                    "execution_plan": execution_plan,
                    "mode_contract": mode_contract,
                    "mode_routing_warnings": [message],
                    "mode_uncertainty_policy": {"applied": False},
                    "mode_routing_metadata": {
                        "requested_mode_raw": requested_mode_raw,
                        "requested_mode_normalized": fallback_mode,
                        "mode_resolution_reason": "engine_exception",
                        "uncertainty_applied": False,
                    },
                    "mode_routing_sources": self._to_string_list(routing_sources),
                },
                metrics={
                    "minister_count": 0,
                    "mode_warning_count": 1,
                    "mode_uncertainty_applied": False,
                    "mode_routing_source_count": len(routing_sources),
                },
                errors=[message],
            )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"mode": self.orchestrator.get_current_mode()})

    @staticmethod
    def _apply_expert_router(
        *,
        context: ExecutionContext,
        routing_context: Mapping[str, Any],
        user_input: str,
        selected_ministers: List[str],
    ) -> Dict[str, float]:
        candidates = (
            ModeRoutingModule._read_normalized_key(context.config, ("expert_router_path",)),
            ModeRoutingModule._read_normalized_key(context.metadata, ("expert_router_path",)),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, ("expert_router_path",)),
            ModeRoutingModule._read_normalized_key(routing_context, ("expert_router_path",)),
        )
        router_path = None
        for candidate in candidates:
            if candidate:
                router_path = candidate
                break

        enabled_candidates = (
            ModeRoutingModule._read_normalized_key(context.config, ("expert_router_enabled",)),
            ModeRoutingModule._read_normalized_key(context.metadata, ("expert_router_enabled",)),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, ("expert_router_enabled",)),
            ModeRoutingModule._read_normalized_key(routing_context, ("expert_router_enabled",)),
        )
        enabled = False
        for candidate in enabled_candidates:
            if isinstance(candidate, bool):
                enabled = candidate
                break
            text = ModeRoutingModule._normalize_text(candidate).lower()
            if text in {"1", "true", "yes", "on"}:
                enabled = True
                break
            if text in {"0", "false", "no", "off"}:
                enabled = False
                break

        if not enabled and not router_path:
            return {}

        predictor = ExpertRouterPredictor(Path(router_path) if router_path else None)
        weights = predictor.predict(user_input, dict(routing_context))

        top_k = None
        for candidate in (
            ModeRoutingModule._read_normalized_key(context.config, ("expert_router_top_k",)),
            ModeRoutingModule._read_normalized_key(context.metadata, ("expert_router_top_k",)),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, ("expert_router_top_k",)),
            ModeRoutingModule._read_normalized_key(routing_context, ("expert_router_top_k",)),
        ):
            if candidate is None:
                continue
            try:
                top_k = int(candidate)
                break
            except (TypeError, ValueError):
                continue

        ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
        if top_k:
            ranked = ranked[: max(1, top_k)]
        return {name: score for name, score in ranked if score > 0}

    @staticmethod
    def _apply_weight_model(
        *,
        context: ExecutionContext,
        routing_context: Mapping[str, Any],
        user_input: str,
    ) -> Dict[str, float]:
        candidates = (
            ModeRoutingModule._read_normalized_key(context.config, ("council_weight_model_path",)),
            ModeRoutingModule._read_normalized_key(context.metadata, ("council_weight_model_path",)),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, ("council_weight_model_path",)),
            ModeRoutingModule._read_normalized_key(routing_context, ("council_weight_model_path",)),
        )
        model_path = None
        for candidate in candidates:
            if candidate:
                model_path = candidate
                break

        enabled_candidates = (
            ModeRoutingModule._read_normalized_key(context.config, ("council_weight_model_enabled",)),
            ModeRoutingModule._read_normalized_key(context.metadata, ("council_weight_model_enabled",)),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, ("council_weight_model_enabled",)),
            ModeRoutingModule._read_normalized_key(routing_context, ("council_weight_model_enabled",)),
        )
        enabled = False
        for candidate in enabled_candidates:
            if isinstance(candidate, bool):
                enabled = candidate
                break
            text = ModeRoutingModule._normalize_text(candidate).lower()
            if text in {"1", "true", "yes", "on"}:
                enabled = True
                break
            if text in {"0", "false", "no", "off"}:
                enabled = False
                break

        if not enabled and not model_path:
            return {}

        predictor = CouncilWeightPredictor(Path(model_path) if model_path else None)
        weights = predictor.predict(user_input, dict(routing_context))

        top_k = None
        for candidate in (
            ModeRoutingModule._read_normalized_key(context.config, ("council_weight_top_k",)),
            ModeRoutingModule._read_normalized_key(context.metadata, ("council_weight_top_k",)),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, ("council_weight_top_k",)),
            ModeRoutingModule._read_normalized_key(routing_context, ("council_weight_top_k",)),
        ):
            if candidate is None:
                continue
            try:
                top_k = int(candidate)
                break
            except (TypeError, ValueError):
                continue

        ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
        if top_k:
            ranked = ranked[: max(1, top_k)]
        return {name: score for name, score in ranked if score > 0}

    @staticmethod
    def _resolve_requested_mode(
        context: ExecutionContext,
        routing_context: Mapping[str, Any],
    ) -> Any:
        keys = ("requested_mode", "mode")
        candidates = (
            ModeRoutingModule._read_normalized_key(context.state, keys),
            ModeRoutingModule._read_normalized_key(context.metadata, keys),
            ModeRoutingModule._read_normalized_key(context.input_contract.metadata, keys),
            ModeRoutingModule._read_normalized_key(context.config, keys),
            ModeRoutingModule._read_normalized_key(routing_context, keys),
        )
        for candidate in candidates:
            normalized = ModeRoutingModule._normalize_mode_candidate(candidate)
            if normalized is None:
                continue
            return normalized
        return "meeting"

    @staticmethod
    def _merge_routing_context(context: ExecutionContext) -> Tuple[Dict[str, Any], List[str]]:
        merged: Dict[str, Any] = {}
        sources: List[str] = []
        routing_keys = ("routing_context",)
        for source_name, payload in (
            (
                "context.config.routing_context",
                ModeRoutingModule._read_normalized_key(context.config, routing_keys),
            ),
            (
                "input.metadata.routing_context",
                ModeRoutingModule._read_normalized_key(context.input_contract.metadata, routing_keys),
            ),
            (
                "run.metadata.routing_context",
                ModeRoutingModule._read_normalized_key(context.metadata, routing_keys),
            ),
            (
                "state.routing_context",
                ModeRoutingModule._read_normalized_key(context.state, routing_keys),
            ),
        ):
            normalized_payload = ModeRoutingModule._normalize_routing_payload(payload)
            if not normalized_payload:
                continue
            merged.update(normalized_payload)
            sources.append(source_name)

        deduped_sources: List[str] = []
        seen = set()
        for source in sources:
            if source in seen:
                continue
            seen.add(source)
            deduped_sources.append(source)
        return merged, deduped_sources

    def _safe_execution_plan(self, mode: str) -> Dict[str, bool]:
        defaults = self._execution_plan_defaults()
        try:
            if not self.orchestrator.set_mode(mode):
                self.orchestrator.set_mode("meeting")
            plan = self.orchestrator.get_execution_plan(self.orchestrator.get_current_mode())
            return self._normalize_execution_plan(plan, defaults=defaults)
        except Exception:
            return defaults

    @staticmethod
    def _execution_plan_defaults() -> Dict[str, bool]:
        return {
            "use_dynamic_council": False,
            "use_ml_prior": False,
            "use_kis": False,
            "use_pwm": False,
            "use_memory": True,
        }

    @staticmethod
    def _normalize_mode_candidate(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)):
            text = bytes(value).decode("utf-8", errors="replace").strip()
            return text or None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, (int, float, bool)):
            text = str(value).strip()
            return text or None
        return None

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = ModeRoutingModule._normalize_text(value).lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return None

    @classmethod
    def _normalize_execution_plan(
        cls,
        value: Any,
        *,
        defaults: Mapping[str, bool],
    ) -> Dict[str, bool]:
        mapping = _coerce_mapping(value) or {}
        normalized = dict(defaults)
        if not mapping:
            return normalized
        key_lookup = {
            cls._normalize_key_name(raw_key): raw_value
            for raw_key, raw_value in mapping.items()
        }
        for key in tuple(defaults.keys()):
            if key not in key_lookup:
                continue
            parsed = cls._to_bool(key_lookup.get(key))
            if parsed is None:
                continue
            normalized[key] = parsed
        return normalized

    @staticmethod
    def _normalize_routing_payload(value: Any) -> Dict[str, Any]:
        return _coerce_mapping(value) or {}

    @staticmethod
    def _to_string_list(value: Any, *, lowercase: bool = False) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [ModeRoutingModule._normalize_text(value)]
        elif isinstance(value, str):
            raw_items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, Iterable):
            items, failed = _coerce_iterable_items(value, preserve_partial=True)
            if failed and not items:
                return []
            raw_items = [ModeRoutingModule._normalize_text(item) for item in items]
        else:
            raw_items = [ModeRoutingModule._normalize_text(value)]

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            ModeRoutingModule._normalize_text(value)
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
        normalized_keys = {ModeRoutingModule._normalize_key_name(key) for key in keys}
        items = (_coerce_mapping(source) or {}).items()
        for raw_key, value in items:
            if ModeRoutingModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None
