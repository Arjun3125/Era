"""Adapter layer for bridging legacy modules into unified orchestration."""

from __future__ import annotations

from .legacy import (
    LEGACY_ENTRYPOINTS,
    LegacyEntrypointPlugin,
    LegacyRunReport,
    build_legacy_plugin,
    list_legacy_entrypoints,
    plugin_stage_handler,
    run_legacy_entrypoint,
)

__all__ = (
    "LEGACY_ENTRYPOINTS",
    "LegacyEntrypointPlugin",
    "LegacyRunReport",
    "build_legacy_plugin",
    "list_legacy_entrypoints",
    "plugin_stage_handler",
    "run_legacy_entrypoint",
)
