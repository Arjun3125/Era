"""Registry for wrapping legacy entrypoints as orchestrator plugins."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .entrypoints import LegacyEntrypointPlugin


@dataclass(frozen=True)
class LegacyEntrypointSpec:
    """Pointer to a legacy callable entrypoint."""

    module_path: str
    callable_name: str

    def __post_init__(self) -> None:
        module_path = str(self.module_path or "").strip()
        callable_name = str(self.callable_name or "").strip()
        if not module_path:
            raise ValueError("LegacyEntrypointSpec.module_path must be non-empty.")
        if not callable_name:
            raise ValueError("LegacyEntrypointSpec.callable_name must be non-empty.")
        object.__setattr__(self, "module_path", module_path)
        object.__setattr__(self, "callable_name", callable_name)


LEGACY_ENTRYPOINTS: Dict[str, LegacyEntrypointSpec] = {
    "persona.main": LegacyEntrypointSpec("persona.main", "main"),
    "system.main": LegacyEntrypointSpec("system_main", "main"),
    "llm.conversation": LegacyEntrypointSpec("llm_conversation", "main"),
}


def list_legacy_entrypoints(*, registry: Mapping[str, LegacyEntrypointSpec] | None = None) -> list[str]:
    """List known legacy entrypoint ids in stable order."""
    table = _resolve_registry(registry)
    return sorted(table.keys())


def build_legacy_plugin(
    entrypoint_id: str,
    *,
    registry: Mapping[str, LegacyEntrypointSpec] | None = None,
) -> LegacyEntrypointPlugin:
    """Resolve and wrap a legacy entrypoint by registry id."""
    normalized_id = _normalize_entrypoint_id(entrypoint_id)
    table = _resolve_registry(registry)
    if normalized_id not in table:
        known = ", ".join(sorted(table.keys())) or "<none>"
        raise KeyError(f"Unknown legacy entrypoint '{entrypoint_id}'. Known: {known}")

    spec = table[normalized_id]
    try:
        module = importlib.import_module(spec.module_path)
    except Exception as exc:
        raise ImportError(
            f"Failed to import module '{spec.module_path}' for legacy entrypoint '{normalized_id}'."
        ) from exc

    try:
        entrypoint = getattr(module, spec.callable_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Legacy entrypoint '{normalized_id}' missing callable "
            f"'{spec.callable_name}' in module '{spec.module_path}'."
        ) from exc
    if not callable(entrypoint):
        raise TypeError(
            f"Legacy entrypoint '{normalized_id}' resolved non-callable "
            f"'{spec.callable_name}' from module '{spec.module_path}'."
        )

    return LegacyEntrypointPlugin(
        plugin_name=normalized_id,
        entrypoint=entrypoint,
    )


def _resolve_registry(
    registry: Mapping[str, LegacyEntrypointSpec] | None,
) -> Dict[str, LegacyEntrypointSpec]:
    source = LEGACY_ENTRYPOINTS if registry is None else registry
    if not isinstance(source, Mapping):
        raise TypeError("registry must be a mapping of entrypoint ids to LegacyEntrypointSpec.")

    normalized: Dict[str, LegacyEntrypointSpec] = {}
    for raw_id, raw_spec in source.items():
        entrypoint_id = _normalize_entrypoint_id(raw_id, field_name="registry key")
        if not isinstance(raw_spec, LegacyEntrypointSpec):
            raise TypeError(
                f"Legacy entrypoint '{entrypoint_id}' registry value must be LegacyEntrypointSpec."
            )
        if entrypoint_id in normalized:
            raise ValueError(
                f"Duplicate legacy entrypoint id after normalization: '{entrypoint_id}'."
            )
        normalized[entrypoint_id] = raw_spec

    return normalized


def _normalize_entrypoint_id(value: Any, *, field_name: str = "entrypoint_id") -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty.")
    return text
