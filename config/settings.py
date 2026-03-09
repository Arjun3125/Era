"""Centralized runtime settings and override normalization utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import os
from typing import Any, Dict, List, Mapping, Tuple


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

RUNTIME_SETTING_FIELDS: Dict[str, str] = {
    "app_name": "str",
    "environment": "str",
    "orchestrator_strict": "bool",
    "observability_enabled": "bool",
    "observability_emit_events": "bool",
    "observability_emit_summary": "bool",
    "observability_write_file": "bool",
    "observability_stderr": "bool",
    "observability_file": "str",
    "decision_pipeline_enabled": "bool",
}

_RUNTIME_KEY_ALIASES: Dict[str, str] = {
    "app_name": "app_name",
    "runtime_app_name": "app_name",
    "era_app_name": "app_name",
    "environment": "environment",
    "env": "environment",
    "runtime_environment": "environment",
    "era_env": "environment",
    "orchestrator_strict": "orchestrator_strict",
    "orch_strict": "orchestrator_strict",
    "runtime_orchestrator_strict": "orchestrator_strict",
    "era_orch_strict": "orchestrator_strict",
    "decision_pipeline_enabled": "decision_pipeline_enabled",
    "runtime_decision_pipeline_enabled": "decision_pipeline_enabled",
    "era_decision_pipeline_enabled": "decision_pipeline_enabled",
    "observability_enabled": "observability_enabled",
    "obs_enabled": "observability_enabled",
    "runtime_observability_enabled": "observability_enabled",
    "era_obs_enabled": "observability_enabled",
    "observability_emit_events": "observability_emit_events",
    "obs_emit_events": "observability_emit_events",
    "runtime_observability_emit_events": "observability_emit_events",
    "era_obs_emit_events": "observability_emit_events",
    "observability_emit_summary": "observability_emit_summary",
    "obs_emit_summary": "observability_emit_summary",
    "runtime_observability_emit_summary": "observability_emit_summary",
    "era_obs_emit_summary": "observability_emit_summary",
    "observability_write_file": "observability_write_file",
    "obs_write_file": "observability_write_file",
    "runtime_observability_write_file": "observability_write_file",
    "era_obs_write_file": "observability_write_file",
    "observability_stderr": "observability_stderr",
    "obs_stderr": "observability_stderr",
    "runtime_observability_stderr": "observability_stderr",
    "era_obs_stderr": "observability_stderr",
    "observability_file": "observability_file",
    "obs_file": "observability_file",
    "runtime_observability_file": "observability_file",
    "era_obs_file": "observability_file",
}


def _as_bool(value: Any, default: bool) -> bool:
    parsed = _parse_bool(value)
    if parsed is None:
        return default
    return parsed


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        return None
    text = _normalize_text(value).lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return None


def _parse_str(value: Any) -> str | None:
    text = _normalize_text(value)
    return text or None


def _dedupe_preserving_order(items: List[str]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _normalize_runtime_key_text(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


def _coerce_strict_flag(value: Any, *, name: str) -> bool:
    parsed = _parse_bool(value)
    if parsed is None:
        raise TypeError(f"{name} must be a boolean.")
    return parsed


def canonicalize_runtime_key(raw_key: Any) -> str | None:
    """Map runtime override key aliases to canonical field names."""
    text = _parse_str(raw_key)
    if text is None:
        return None

    normalized = _normalize_runtime_key_text(text)
    canonical = _RUNTIME_KEY_ALIASES.get(normalized)
    if canonical:
        return canonical
    if normalized in RUNTIME_SETTING_FIELDS:
        return normalized
    if normalized.startswith("era_runtime_"):
        candidate = normalized[len("era_runtime_") :]
        if candidate in RUNTIME_SETTING_FIELDS:
            return candidate
    if normalized.startswith("runtime_"):
        candidate = normalized[len("runtime_") :]
        if candidate in RUNTIME_SETTING_FIELDS:
            return candidate
    if normalized.startswith("settings_"):
        candidate = normalized[len("settings_") :]
        if candidate in RUNTIME_SETTING_FIELDS:
            return candidate
    return None


def normalize_runtime_overrides(
    overrides: Mapping[str, Any] | None,
    *,
    strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """Normalize user-provided runtime setting overrides.

    Returns normalized overrides plus warnings for unknown/invalid entries.
    Raises ValueError when strict=True and any invalid override is encountered.
    """
    strict_enabled = _coerce_strict_flag(strict, name="strict")
    if overrides is None:
        return {}, []
    if not isinstance(overrides, Mapping):
        raise TypeError("Runtime overrides must be a mapping.")
    if not overrides:
        return {}, []

    normalized: Dict[str, Any] = {}
    warnings: List[str] = []
    seen_raw_key_by_canonical: Dict[str, str] = {}
    for raw_key, raw_value in _coerce_mapping_items(overrides):
        raw_key_text = _normalize_text(raw_key)
        key = canonicalize_runtime_key(raw_key_text)
        kind = RUNTIME_SETTING_FIELDS.get(str(key))
        if not kind:
            message = f"Unknown runtime setting '{raw_key_text}' ignored."
            if strict_enabled:
                raise ValueError(message)
            warnings.append(message)
            continue

        if key in normalized and seen_raw_key_by_canonical.get(key) != raw_key_text:
            message = (
                f"Duplicate runtime setting alias '{raw_key_text}' "
                f"overrides '{seen_raw_key_by_canonical.get(key)}'."
            )
            if strict_enabled:
                raise ValueError(message)
            warnings.append(message)

        if kind == "bool":
            parsed = _parse_bool(raw_value)
            if parsed is None:
                message = f"Invalid boolean for runtime setting '{key}' ignored."
                if strict_enabled:
                    raise ValueError(message)
                warnings.append(message)
                continue
            normalized[key] = parsed
            seen_raw_key_by_canonical[key] = raw_key_text
            continue

        parsed_str = _parse_str(raw_value)
        if parsed_str is None:
            message = f"Invalid string for runtime setting '{key}' ignored."
            if strict_enabled:
                raise ValueError(message)
            warnings.append(message)
            continue
        normalized[key] = parsed_str
        seen_raw_key_by_canonical[key] = raw_key_text

    return normalized, _dedupe_preserving_order(warnings)


@dataclass(frozen=True)
class RuntimeSettings:
    """Core runtime settings used by orchestrated wrappers."""

    app_name: str = "era"
    environment: str = "development"
    orchestrator_strict: bool = False

    observability_enabled: bool = True
    observability_emit_events: bool = False
    observability_emit_summary: bool = True
    observability_write_file: bool = False
    observability_stderr: bool = False
    observability_file: str = "logs/orchestration_events.jsonl"
    decision_pipeline_enabled: bool = True

    def enforce_invariants(self) -> Tuple["RuntimeSettings", List[str]]:
        """Normalize dependent settings to keep runtime behavior coherent."""
        warnings: List[str] = []
        updates: Dict[str, Any] = {}
        resolved_bools: Dict[str, bool] = {}

        app_name = _parse_str(self.app_name)
        if app_name is None:
            updates["app_name"] = "era"
            warnings.append("app_name was empty; defaulted to 'era'.")

        environment = _parse_str(self.environment)
        if environment is None:
            updates["environment"] = "development"
            warnings.append("environment was empty; defaulted to 'development'.")

        for field_name, default_value in (
            ("orchestrator_strict", False),
            ("observability_enabled", True),
            ("observability_emit_events", False),
            ("observability_emit_summary", True),
            ("observability_write_file", False),
            ("observability_stderr", False),
            ("decision_pipeline_enabled", True),
        ):
            raw_value = getattr(self, field_name)
            parsed_value = _parse_bool(raw_value)
            if parsed_value is None:
                updates[field_name] = default_value
                resolved_bools[field_name] = default_value
                warnings.append(
                    f"{field_name} had invalid boolean value; defaulted to {default_value}."
                )
                continue
            resolved_bools[field_name] = parsed_value
            if type(raw_value) is not bool or parsed_value != raw_value:
                updates[field_name] = parsed_value

        if not resolved_bools.get("observability_enabled", bool(self.observability_enabled)):
            for field_name in (
                "observability_emit_events",
                "observability_emit_summary",
                "observability_write_file",
                "observability_stderr",
            ):
                if resolved_bools.get(field_name, bool(getattr(self, field_name))):
                    updates[field_name] = False
                    warnings.append(
                        f"{field_name} disabled because observability_enabled is false."
                    )

        if resolved_bools.get("observability_write_file", bool(self.observability_write_file)):
            obs_file = _parse_str(self.observability_file)
            if obs_file is None:
                updates["observability_file"] = "logs/orchestration_events.jsonl"
                warnings.append(
                    "observability_file was empty while observability_write_file is true; "
                    "default path applied."
                )

        if not updates:
            return self, _dedupe_preserving_order(warnings)
        return replace(self, **updates), _dedupe_preserving_order(warnings)

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        """Build settings from environment with stable defaults."""
        settings = cls(
            app_name=_parse_str(os.getenv("ERA_APP_NAME", "era")) or "era",
            environment=_parse_str(os.getenv("ERA_ENV", "development")) or "development",
            orchestrator_strict=_as_bool(
                os.getenv("ERA_ORCH_STRICT"),
                False,
            ),
            observability_enabled=_as_bool(
                os.getenv("ERA_OBS_ENABLED"),
                True,
            ),
            observability_emit_events=_as_bool(
                os.getenv("ERA_OBS_EMIT_EVENTS"),
                False,
            ),
            observability_emit_summary=_as_bool(
                os.getenv("ERA_OBS_EMIT_SUMMARY"),
                True,
            ),
            observability_write_file=_as_bool(
                os.getenv("ERA_OBS_WRITE_FILE"),
                False,
            ),
            observability_stderr=_as_bool(
                os.getenv("ERA_OBS_STDERR"),
                False,
            ),
            observability_file=os.getenv(
                "ERA_OBS_FILE",
                "logs/orchestration_events.jsonl",
            ),
            decision_pipeline_enabled=_as_bool(
                os.getenv("ERA_DECISION_PIPELINE_ENABLED"),
                True,
            ),
        )
        normalized_settings, _ = settings.enforce_invariants()
        return normalized_settings

    def apply_overrides(
        self,
        overrides: Mapping[str, Any] | None,
        *,
        strict: bool = False,
    ) -> Tuple["RuntimeSettings", List[str]]:
        """Apply runtime override mapping over current settings."""
        strict_enabled = _coerce_strict_flag(strict, name="strict")
        if overrides is not None and not isinstance(overrides, Mapping):
            raise TypeError("Runtime overrides must be a mapping.")
        normalized, warnings = normalize_runtime_overrides(
            overrides,
            strict=strict_enabled,
        )
        if not normalized:
            current, invariant_warnings = self.enforce_invariants()
            warnings.extend(invariant_warnings)
            return current, _dedupe_preserving_order(warnings)
        updated = replace(self, **normalized)
        updated, invariant_warnings = updated.enforce_invariants()
        warnings.extend(invariant_warnings)
        return updated, _dedupe_preserving_order(warnings)

    def to_dict(self) -> Dict[str, Any]:
        """Export settings as primitive dictionary."""
        return asdict(self)


def load_runtime_settings(
    *,
    overrides: Mapping[str, Any] | None = None,
    strict_overrides: bool = False,
) -> RuntimeSettings:
    """Public loader for shared runtime settings.

    Invalid overrides are ignored unless strict_overrides=True.
    """
    strict_enabled = _coerce_strict_flag(strict_overrides, name="strict_overrides")
    settings, _ = load_runtime_settings_report(
        overrides,
        strict=strict_enabled,
    )
    return settings


def load_runtime_settings_report(
    overrides: Mapping[str, Any] | None = None,
    *,
    strict: bool = False,
) -> Tuple[RuntimeSettings, List[str]]:
    """Load runtime settings with normalization warnings."""
    strict_enabled = _coerce_strict_flag(strict, name="strict")
    if overrides is not None and not isinstance(overrides, Mapping):
        raise TypeError("Runtime overrides must be a mapping.")
    settings = RuntimeSettings.from_env()
    settings, warnings = settings.apply_overrides(
        overrides,
        strict=strict_enabled,
    )
    return settings, _dedupe_preserving_order(warnings)


def _coerce_mapping_items(value: Mapping[str, Any]) -> List[tuple[Any, Any]]:
    try:
        return list(value.items())
    except Exception as exc:
        raise TypeError("Runtime overrides must be a mapping.") from exc
