"""Legacy adapter utilities for staged migration."""

from .entrypoints import LegacyEntrypointPlugin, plugin_stage_handler
from .registry import LEGACY_ENTRYPOINTS, build_legacy_plugin, list_legacy_entrypoints
from .runner import LegacyRunReport, run_legacy_entrypoint

__all__ = [
    "LEGACY_ENTRYPOINTS",
    "LegacyRunReport",
    "LegacyEntrypointPlugin",
    "build_legacy_plugin",
    "list_legacy_entrypoints",
    "plugin_stage_handler",
    "run_legacy_entrypoint",
]
