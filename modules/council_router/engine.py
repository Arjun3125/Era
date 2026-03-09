"""Deterministic mode routing engine for the decision pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import Any, Dict, List, Mapping

from core.contracts import ModeResolutionContract

from .mode_orchestrator import ModeOrchestrator


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

_ABLATED_KEYS = (
    "disable_ministers",
    "disable_kis",
    "disable_ml_prior",
    "disable_pwm",
    "disable_mode_escalation",
)


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


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _normalize_key_name(value: Any) -> str:
    return (
        _normalize_text(value)
        .lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


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
        key = _normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class ModeRoutingResult:
    """Normalized mode routing output consumed by pipeline stage wrapper."""

    resolved_mode: str
    should_invoke_council: bool
    selected_ministers: List[str]
    frame: str
    execution_plan: Dict[str, bool]
    mode_contract: ModeResolutionContract
    warnings: List[str]
    uncertainty_policy: Dict[str, Any]
    routing_metadata: Dict[str, Any]


@dataclass
class ModeRoutingEngine:
    """Resolves requested mode into deterministic routing outputs."""

    orchestrator: ModeOrchestrator
    default_mode: str = "meeting"

    def route(
        self,
        *,
        requested_mode: Any,
        user_input: str,
        routing_context: Mapping[str, Any] | None = None,
    ) -> ModeRoutingResult:
        warnings: List[str] = []
        context = self._coerce_routing_context(routing_context, warnings)
        base_ablation = self._current_ablation_config()

        try:
            normalized_mode, mode_metadata = self._normalize_requested_mode(
                requested_mode,
                warnings,
            )
            self.orchestrator.set_mode(normalized_mode)
            resolved_mode = self.orchestrator.get_current_mode()

            self._apply_ablation_overrides(context, warnings)
            execution_plan = self._normalize_execution_plan(
                self.orchestrator.get_execution_plan(resolved_mode),
                resolved_mode=resolved_mode,
                warnings=warnings,
            )

            uncertainty_policy = self._apply_uncertainty_control(
                resolved_mode=resolved_mode,
                routing_context=context,
                warnings=warnings,
            )
            if uncertainty_policy.get("applied"):
                target = str(uncertainty_policy.get("target_mode", resolved_mode)).strip().lower()
                if target and target != resolved_mode:
                    if self.orchestrator.set_mode(target):
                        resolved_mode = self.orchestrator.get_current_mode()
                        execution_plan = self._normalize_execution_plan(
                            self.orchestrator.get_execution_plan(resolved_mode),
                            resolved_mode=resolved_mode,
                            warnings=warnings,
                        )
                    else:
                        warnings.append(
                            f"Uncertainty target mode '{target}' ignored; unsupported by orchestrator."
                        )

            should_invoke = self.orchestrator.should_invoke_council(resolved_mode)
            ministers = self._normalize_ministers(
                self.orchestrator.get_ministers_for_mode(resolved_mode, context),
            )
            frame = self.orchestrator.frame_for_mode(user_input, resolved_mode, context)

            confidence = self._resolve_confidence(
                resolved_mode=resolved_mode,
                mode_metadata=mode_metadata,
                uncertainty_policy=uncertainty_policy,
            )
            mode_contract = ModeResolutionContract(
                mode=resolved_mode,
                should_invoke_council=should_invoke,
                selected_ministers=ministers,
                rationale=frame,
                confidence=confidence,
            )
            routing_metadata = {
                "requested_mode_raw": requested_mode,
                "requested_mode_normalized": normalized_mode,
                "mode_resolution_reason": mode_metadata.get("reason", "direct"),
                "uncertainty_applied": bool(uncertainty_policy.get("applied")),
            }

            return ModeRoutingResult(
                resolved_mode=resolved_mode,
                should_invoke_council=should_invoke,
                selected_ministers=ministers,
                frame=frame,
                execution_plan=execution_plan,
                mode_contract=mode_contract,
                warnings=self._dedupe_warnings(warnings),
                uncertainty_policy=uncertainty_policy,
                routing_metadata=routing_metadata,
            )
        finally:
            self._restore_ablation_config(base_ablation)

    def _normalize_requested_mode(
        self,
        requested_mode: Any,
        warnings: List[str],
    ) -> tuple[str, Dict[str, str]]:
        raw = _normalize_text(requested_mode).lower()
        if not raw:
            warnings.append(
                f"Missing requested mode normalized to '{self.default_mode}'."
            )
            return self.default_mode, {"reason": "missing"}

        normalized = _MODE_ALIASES.get(raw, raw)
        valid_modes = set(self.orchestrator.list_modes())
        if normalized not in valid_modes:
            warnings.append(
                f"Unsupported mode '{raw}' normalized to '{self.default_mode}'."
            )
            return self.default_mode, {"reason": "unsupported"}

        if normalized != raw:
            warnings.append(f"Mode alias '{raw}' normalized to '{normalized}'.")
            return normalized, {"reason": "alias"}

        return normalized, {"reason": "direct"}

    def _apply_ablation_overrides(
        self,
        routing_context: Mapping[str, Any],
        warnings: List[str],
    ) -> None:
        source = routing_context.get("ablation")
        payload = self._coerce_mapping(
            source,
            warnings=warnings,
            field_name="routing_context.ablation",
        )
        for key in _ABLATED_KEYS:
            value = self._read_normalized_key(routing_context, key)
            if value is not None:
                payload[key] = value

        if not payload:
            return

        current = self.orchestrator.config
        updates: Dict[str, bool] = {}
        for key in _ABLATED_KEYS:
            if key not in payload:
                continue
            parsed = self._to_bool(payload.get(key))
            if parsed is None:
                warnings.append(f"Invalid ablation flag '{key}' ignored.")
                continue
            updates[key] = parsed
            if bool(getattr(current, key, False)) != parsed:
                warnings.append(f"Ablation flag '{key}' set to {parsed}.")

        if updates:
            self.orchestrator.set_ablation_config(
                disable_ministers=updates.get("disable_ministers", current.disable_ministers),
                disable_kis=updates.get("disable_kis", current.disable_kis),
                disable_ml_prior=updates.get("disable_ml_prior", current.disable_ml_prior),
                disable_pwm=updates.get("disable_pwm", current.disable_pwm),
                disable_mode_escalation=updates.get(
                    "disable_mode_escalation",
                    current.disable_mode_escalation,
                ),
            )

    def _apply_uncertainty_control(
        self,
        *,
        resolved_mode: str,
        routing_context: Mapping[str, Any],
        warnings: List[str],
    ) -> Dict[str, Any]:
        signals = routing_context.get("uncertainty_signals")
        enabled_flag = routing_context.get("use_uncertainty_control")
        enabled = self._to_bool(enabled_flag)
        if enabled is None and enabled_flag is not None:
            warnings.append("Invalid uncertainty control flag ignored.")
        signals_mapping = self._coerce_mapping(
            signals,
            warnings=warnings,
            field_name="routing_context.uncertainty_signals",
        )
        if not signals_mapping or enabled is not True:
            return {"applied": False}

        policy_raw = self.orchestrator.apply_uncertainty_control(
            signals=dict(signals_mapping),
            base_mode=resolved_mode,
        )
        if not isinstance(policy_raw, Mapping):
            warnings.append("Invalid uncertainty policy payload ignored.")
            return {"applied": False}

        policy = dict(policy_raw)
        target = str(policy.get("target_mode", resolved_mode)).strip().lower()
        if not target:
            target = resolved_mode
        applied = bool(target) and target != resolved_mode
        if applied:
            warnings.append(
                f"Uncertainty control escalated mode from '{resolved_mode}' to '{target}'."
            )
        return {
            "applied": applied,
            **policy,
            "target_mode": target,
        }

    @staticmethod
    def _normalize_ministers(ministers: Any) -> List[str]:
        if isinstance(ministers, Mapping):
            try:
                items = list(ministers.keys())
            except Exception:
                items = []
        elif isinstance(ministers, str):
            items = [part.strip() for part in ministers.split(",")]
        elif isinstance(ministers, Iterable):
            items, _ = _coerce_iterable_items(ministers, preserve_partial=True)
        else:
            items = []
        normalized: List[str] = []
        seen = set()
        for item in items:
            text = _normalize_text(item).lower()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized

    @staticmethod
    def _resolve_confidence(
        *,
        resolved_mode: str,
        mode_metadata: Mapping[str, str],
        uncertainty_policy: Mapping[str, Any],
    ) -> float:
        reason = str(mode_metadata.get("reason", "direct"))
        if reason == "direct":
            confidence = 1.0
        elif reason == "alias":
            confidence = 0.95
        else:
            confidence = 0.75

        if bool(uncertainty_policy.get("applied")):
            confidence = min(confidence, 0.85)
            target = str(uncertainty_policy.get("target_mode", "")).strip().lower()
            if target == "darbar" and resolved_mode == "darbar":
                confidence = min(confidence, 0.8)
        return max(0.0, min(1.0, confidence))

    def _current_ablation_config(self) -> Dict[str, bool]:
        config = self.orchestrator.config
        return {
            "disable_ministers": bool(config.disable_ministers),
            "disable_kis": bool(config.disable_kis),
            "disable_ml_prior": bool(config.disable_ml_prior),
            "disable_pwm": bool(config.disable_pwm),
            "disable_mode_escalation": bool(config.disable_mode_escalation),
        }

    def _restore_ablation_config(self, snapshot: Mapping[str, bool]) -> None:
        self.orchestrator.set_ablation_config(
            disable_ministers=bool(snapshot.get("disable_ministers", False)),
            disable_kis=bool(snapshot.get("disable_kis", False)),
            disable_ml_prior=bool(snapshot.get("disable_ml_prior", False)),
            disable_pwm=bool(snapshot.get("disable_pwm", False)),
            disable_mode_escalation=bool(snapshot.get("disable_mode_escalation", False)),
        )

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
    def _coerce_mapping(value: Any, *, warnings: List[str], field_name: str) -> Dict[str, Any]:
        mapping_like = _coerce_mapping_like(value)
        if mapping_like is not None:
            return mapping_like
        if value in (None, ""):
            return {}
        if isinstance(value, (str, bytes, bytearray)):
            text = _normalize_text(value)
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
                return {}
            parsed_mapping_like = _coerce_mapping_like(parsed)
            if parsed_mapping_like is not None:
                return parsed_mapping_like
            warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
            return {}
        warnings.append(f"Invalid {field_name} payload normalized to empty mapping.")
        return {}

    def _coerce_routing_context(
        self,
        value: Any,
        warnings: List[str],
    ) -> Dict[str, Any]:
        return self._coerce_mapping(
            value,
            warnings=warnings,
            field_name="routing_context",
        )

    @staticmethod
    def _read_normalized_key(source: Mapping[str, Any], key: str) -> Any:
        normalized_target = _normalize_key_name(key)
        try:
            items = source.items()
        except Exception:
            return None
        for raw_key, value in items:
            if _normalize_key_name(raw_key) == normalized_target:
                return value
        return None

    @staticmethod
    def _default_execution_plan_for_mode(mode: str) -> Dict[str, bool]:
        normalized = _normalize_text(mode).lower()
        if normalized == "baseline":
            return {
                "use_dynamic_council": False,
                "use_ml_prior": False,
                "use_kis": False,
                "use_pwm": False,
                "use_memory": False,
            }
        return {
            "use_dynamic_council": True,
            "use_ml_prior": True,
            "use_kis": True,
            "use_pwm": True,
            "use_memory": True,
        }

    @classmethod
    def _normalize_execution_plan(
        cls,
        plan: Any,
        *,
        resolved_mode: str,
        warnings: List[str],
    ) -> Dict[str, bool]:
        defaults = cls._default_execution_plan_for_mode(resolved_mode)
        plan_mapping = cls._coerce_mapping(
            plan,
            warnings=warnings,
            field_name="execution_plan",
        )
        if not plan_mapping:
            return defaults

        normalized = dict(defaults)
        key_lookup = {
            _normalize_key_name(raw_key): value
            for raw_key, value in plan_mapping.items()
        }
        for key in tuple(defaults.keys()):
            if key not in key_lookup:
                continue
            parsed = cls._to_bool(key_lookup.get(key))
            if parsed is None:
                warnings.append(f"Invalid execution plan flag '{key}' normalized to default.")
                continue
            normalized[key] = parsed
        return normalized
