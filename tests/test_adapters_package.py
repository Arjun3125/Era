"""Tests for top-level adapters package exports."""

from __future__ import annotations

from adapters import (
    LEGACY_ENTRYPOINTS,
    LegacyEntrypointPlugin,
    LegacyRunReport,
    build_legacy_plugin,
    list_legacy_entrypoints,
    plugin_stage_handler,
    run_legacy_entrypoint,
)


def test_adapters_package_exposes_legacy_bridge_symbols():
    assert isinstance(LEGACY_ENTRYPOINTS, dict)
    assert callable(build_legacy_plugin)
    assert callable(list_legacy_entrypoints)
    assert callable(plugin_stage_handler)
    assert callable(run_legacy_entrypoint)
    assert LegacyEntrypointPlugin.__name__ == "LegacyEntrypointPlugin"
    assert LegacyRunReport.__name__ == "LegacyRunReport"
