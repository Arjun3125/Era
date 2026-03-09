"""Runtime configuration resolution engine for orchestrated pipeline runs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from config import (
    RuntimeSettings,
    canonicalize_runtime_key,
    load_runtime_settings_report,
    normalize_runtime_overrides,
)
from core.contracts import RuntimeConfigContract


_OVERRIDE_KEYS = (
    "runtime_settings",
    "runtime_config",
    "runtime_config_overrides",
    "settings_overrides",
    "runtime_overrides",
)

_STRICT_OVERRIDE_KEYS = (
    "runtime_overrides_strict",
    "runtime_strict_overrides",
    "strict_runtime_overrides",
)

_SOURCE_ORDER = (
    ("context.config", "context_config"),
    ("input.metadata", "input_metadata"),
    ("run.metadata", "metadata"),
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _normalize_key_text(value: Any) -> str:
    return (
        _normalize_text(value)
        .lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


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


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        try:
            source_items = value.items()
        except Exception:
            return {}
        raw_items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        iterable_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
            return {}
        raw_items = []
        for item in iterable_items:
            if isinstance(item, Mapping):
                return {}
            try:
                key, item_value = item
            except Exception:
                return {}
            raw_items.append((key, item_value))
    else:
        return {}

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in raw_items:
        key = _normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


_NORMALIZED_OVERRIDE_KEYS = {_normalize_key_text(item) for item in _OVERRIDE_KEYS}
_NORMALIZED_OVERRIDE_KEY_TO_NAME = {
    _normalize_key_text(item): item for item in _OVERRIDE_KEYS
}
_NORMALIZED_STRICT_OVERRIDE_KEYS = {_normalize_key_text(item) for item in _STRICT_OVERRIDE_KEYS}
_RUNTIME_CONTAINER_KEY = _normalize_key_text("runtime")
_SETTINGS_CONTAINER_KEY = _normalize_key_text("settings")


@dataclass
class RuntimeConfigResult:
    """Normalized config payload produced by runtime config resolution."""

    settings: RuntimeSettings
    contract: RuntimeConfigContract
    settings_dict: Dict[str, Any]
    warnings: List[str]


@dataclass
class RuntimeConfigEngine:
    """Resolves runtime settings from environment + optional explicit overrides."""

    def resolve(
        self,
        *,
        context_config: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        input_metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeConfigResult:
        settings, warnings = load_runtime_settings_report()
        strict_overrides, strict_warnings = self._resolve_strict_override_mode(
            context_config=context_config,
            metadata=metadata,
            input_metadata=input_metadata,
        )
        warnings.extend(strict_warnings)

        merged_overrides: Dict[str, Any] = {}
        override_sources: List[str] = []
        last_override_source: Dict[str, str] = {}
        for source_name, override_map in self._iter_override_maps(
            context_config=context_config,
            metadata=metadata,
            input_metadata=input_metadata,
        ):
            normalized, source_warnings = normalize_runtime_overrides(
                override_map,
                strict=strict_overrides,
            )
            warnings.extend([f"{source_name}: {message}" for message in source_warnings])
            for key, value in normalized.items():
                previous_source = last_override_source.get(key)
                if previous_source is not None and merged_overrides.get(key) != value:
                    warnings.append(
                        f"{source_name}: runtime setting '{key}' overrides value from {previous_source}."
                    )
                merged_overrides[key] = value
                last_override_source[key] = source_name
                override_sources.append(f"{source_name}:{key}")

        if merged_overrides:
            settings, apply_warnings = settings.apply_overrides(
                merged_overrides,
                strict=strict_overrides,
            )
            warnings.extend([f"runtime.apply: {message}" for message in apply_warnings])

        settings_dict = settings.to_dict()
        overrides_applied = sorted(set(merged_overrides.keys()))
        source = "environment+overrides" if overrides_applied else "environment"
        settings_dict["overrides_applied"] = list(overrides_applied)
        settings_dict["runtime_overrides_strict"] = bool(strict_overrides)

        if override_sources:
            settings_dict["override_sources"] = self._dedupe_preserving_order(override_sources)

        contract = RuntimeConfigContract(
            app_name=str(settings.app_name),
            environment=str(settings.environment),
            orchestrator_strict=bool(settings.orchestrator_strict),
            decision_pipeline_enabled=bool(settings.decision_pipeline_enabled),
            observability_enabled=bool(settings.observability_enabled),
            observability_emit_events=bool(settings.observability_emit_events),
            observability_emit_summary=bool(settings.observability_emit_summary),
            observability_write_file=bool(settings.observability_write_file),
            observability_stderr=bool(settings.observability_stderr),
            observability_file=str(settings.observability_file),
            source=source,
            overrides_applied=overrides_applied,
        )

        return RuntimeConfigResult(
            settings=settings,
            contract=contract,
            settings_dict=settings_dict,
            warnings=self._dedupe_preserving_order(warnings),
        )

    def _iter_override_maps(
        self,
        *,
        context_config: Mapping[str, Any] | None,
        metadata: Mapping[str, Any] | None,
        input_metadata: Mapping[str, Any] | None,
    ):
        source_maps = {
            "context_config": context_config,
            "metadata": metadata,
            "input_metadata": input_metadata,
        }
        for source_name, source_map in self._iter_source_maps(source_maps):
            for map_name, override_map in self._iter_override_map_payloads(source_map):
                yield f"{source_name}.{map_name}", override_map

    def _resolve_strict_override_mode(
        self,
        *,
        context_config: Mapping[str, Any] | None,
        metadata: Mapping[str, Any] | None,
        input_metadata: Mapping[str, Any] | None,
    ) -> Tuple[bool, List[str]]:
        strict = False
        warnings: List[str] = []
        source_maps = {
            "context_config": context_config,
            "metadata": metadata,
            "input_metadata": input_metadata,
        }

        for source_name, source_map in self._iter_source_maps(source_maps):
            for strict_source, raw_value in self._iter_strict_flag_candidates(source_map):
                parsed = self._parse_bool(raw_value)
                if parsed is None:
                    warnings.append(
                        f"{source_name}.{strict_source}: "
                        "invalid boolean for runtime strict-overrides ignored."
                    )
                    continue
                strict = parsed
        return strict, warnings

    @staticmethod
    def _iter_source_maps(
        source_maps: Mapping[str, Mapping[str, Any] | None],
    ):
        for source_name, source_key in _SOURCE_ORDER:
            source_map = source_maps.get(source_key)
            coerced = _coerce_mapping(source_map)
            if not coerced:
                continue
            yield source_name, coerced

    def _iter_override_map_payloads(self, source_map: Mapping[str, Any]):
        for normalized_key, payload in self._iter_known_mapping_payloads(
            source_map,
            allowed_keys=_NORMALIZED_OVERRIDE_KEYS,
        ):
            key = _NORMALIZED_OVERRIDE_KEY_TO_NAME.get(normalized_key, normalized_key)
            payload_mapping = _coerce_mapping(payload)
            if payload_mapping:
                cleaned = self._remove_strict_control_keys(payload_mapping)
                if cleaned:
                    yield key, cleaned

        runtime_payload = self._get_mapping_value_by_normalized_key(
            source_map,
            _RUNTIME_CONTAINER_KEY,
        )
        runtime_payload_mapping = _coerce_mapping(runtime_payload)
        if runtime_payload_mapping:
            for normalized_key, payload in self._iter_known_mapping_payloads(
                runtime_payload_mapping,
                allowed_keys=_NORMALIZED_OVERRIDE_KEYS,
            ):
                key = _NORMALIZED_OVERRIDE_KEY_TO_NAME.get(normalized_key, normalized_key)
                payload_mapping = _coerce_mapping(payload)
                if payload_mapping:
                    cleaned = self._remove_strict_control_keys(payload_mapping)
                    if cleaned:
                        yield f"runtime.{key}", cleaned

            nested_settings = self._get_mapping_value_by_normalized_key(
                runtime_payload_mapping,
                _SETTINGS_CONTAINER_KEY,
            )
            nested_settings_mapping = _coerce_mapping(nested_settings)
            if nested_settings_mapping:
                cleaned = self._remove_strict_control_keys(nested_settings_mapping)
                if cleaned:
                    yield "runtime.settings", cleaned

        direct_overrides = self._extract_direct_overrides(source_map)
        if direct_overrides:
            yield "direct", direct_overrides

    @staticmethod
    def _iter_strict_flag_candidates(source_map: Mapping[str, Any]):
        normalized_source_map = _coerce_mapping(source_map)
        for key, value in normalized_source_map.items():
            if RuntimeConfigEngine._is_strict_override_key(key):
                yield _normalize_text(key), value

        for normalized_container, payload in RuntimeConfigEngine._iter_known_mapping_payloads(
            normalized_source_map,
            allowed_keys=_NORMALIZED_OVERRIDE_KEYS,
        ):
            payload_mapping = _coerce_mapping(payload)
            if not payload_mapping:
                continue
            container = _NORMALIZED_OVERRIDE_KEY_TO_NAME.get(
                normalized_container,
                normalized_container,
            )
            for key, value in payload_mapping.items():
                if RuntimeConfigEngine._is_strict_override_key(key):
                    yield f"{container}.{_normalize_text(key)}", value

        runtime_payload = RuntimeConfigEngine._get_mapping_value_by_normalized_key(
            normalized_source_map,
            _RUNTIME_CONTAINER_KEY,
        )
        runtime_payload_mapping = _coerce_mapping(runtime_payload)
        if runtime_payload_mapping:
            for key, value in runtime_payload_mapping.items():
                if RuntimeConfigEngine._is_strict_override_key(key):
                    yield f"runtime.{_normalize_text(key)}", value
            nested_settings = RuntimeConfigEngine._get_mapping_value_by_normalized_key(
                runtime_payload_mapping,
                _SETTINGS_CONTAINER_KEY,
            )
            nested_settings_mapping = _coerce_mapping(nested_settings)
            if nested_settings_mapping:
                for key, value in nested_settings_mapping.items():
                    if RuntimeConfigEngine._is_strict_override_key(key):
                        yield f"runtime.settings.{_normalize_text(key)}", value

    @staticmethod
    def _parse_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        normalized = _normalize_text(value).lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return None

    @staticmethod
    def _extract_direct_overrides(source_map: Mapping[str, Any]) -> Dict[str, Any]:
        """Collect direct runtime overrides from a source map."""
        direct: Dict[str, Any] = {}
        for raw_key, value in _coerce_mapping(source_map).items():
            key = _normalize_text(raw_key)
            if not key:
                continue
            if RuntimeConfigEngine._is_override_control_key(key):
                continue
            canonical = canonicalize_runtime_key(key)
            if canonical is None:
                continue
            direct[key] = value
        return direct

    @staticmethod
    def _remove_strict_control_keys(payload: Mapping[str, Any]) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for raw_key, value in _coerce_mapping(payload).items():
            if RuntimeConfigEngine._is_strict_override_key(raw_key):
                continue
            key = _normalize_text(raw_key)
            if not key:
                continue
            cleaned[key] = value
        return cleaned

    @staticmethod
    def _is_override_control_key(raw_key: Any) -> bool:
        normalized = _normalize_key_text(raw_key)
        return (
            normalized in _NORMALIZED_OVERRIDE_KEYS
            or normalized in _NORMALIZED_STRICT_OVERRIDE_KEYS
            or normalized == _RUNTIME_CONTAINER_KEY
        )

    @staticmethod
    def _is_strict_override_key(raw_key: Any) -> bool:
        return _normalize_key_text(raw_key) in _NORMALIZED_STRICT_OVERRIDE_KEYS

    @staticmethod
    def _iter_known_mapping_payloads(
        value: Mapping[str, Any],
        *,
        allowed_keys: set[str],
    ):
        for raw_key, payload in _coerce_mapping(value).items():
            normalized_key = _normalize_key_text(raw_key)
            if normalized_key in allowed_keys:
                yield normalized_key, payload

    @staticmethod
    def _get_mapping_value_by_normalized_key(
        value: Mapping[str, Any],
        normalized_key: str,
    ) -> Any:
        for raw_key, payload in _coerce_mapping(value).items():
            if _normalize_key_text(raw_key) == normalized_key:
                return payload
        return None

    @staticmethod
    def _dedupe_preserving_order(values: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped
