"""Tests for legacy entrypoint registry and plugin construction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from adapters.legacy.entrypoints import LegacyEntrypointPlugin
from adapters.legacy.registry import (
    LegacyEntrypointSpec,
    build_legacy_plugin,
    list_legacy_entrypoints,
)


def test_spec_validates_non_empty_fields():
    with pytest.raises(ValueError, match="module_path must be non-empty"):
        LegacyEntrypointSpec(" ", "main")
    with pytest.raises(ValueError, match="callable_name must be non-empty"):
        LegacyEntrypointSpec("pkg.mod", " ")


def test_list_legacy_entrypoints_returns_sorted_keys():
    keys = list_legacy_entrypoints(
        registry={
            "zeta.main": LegacyEntrypointSpec("zeta.main", "main"),
            "alpha.main": LegacyEntrypointSpec("alpha.main", "main"),
        }
    )
    assert keys == ["alpha.main", "zeta.main"]


def test_list_legacy_entrypoints_honors_explicit_empty_registry():
    assert list_legacy_entrypoints(registry={}) == []


def test_build_legacy_plugin_validates_entrypoint_id_and_unknown():
    with pytest.raises(ValueError, match="entrypoint_id must be non-empty"):
        build_legacy_plugin(" ")
    with pytest.raises(KeyError, match="Unknown legacy entrypoint"):
        build_legacy_plugin(
            "missing.main",
            registry={"known.main": LegacyEntrypointSpec("known.main", "main")},
        )


def test_build_legacy_plugin_rejects_invalid_registry_entries():
    with pytest.raises(TypeError, match="must be LegacyEntrypointSpec"):
        build_legacy_plugin("x.y", registry={"x.y": object()})  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Duplicate legacy entrypoint id after normalization"):
        build_legacy_plugin(
            "x.y",
            registry={
                "x.y": LegacyEntrypointSpec("pkg.one", "main"),
                " x.y ": LegacyEntrypointSpec("pkg.two", "main"),
            },
        )


def test_build_legacy_plugin_wraps_import_and_resolution_failures(monkeypatch):
    spec = LegacyEntrypointSpec("x.y", "main")
    registry = {"x.y": spec}

    def _import_fail(_module_path):
        raise ModuleNotFoundError("missing")

    monkeypatch.setattr("adapters.legacy.registry.importlib.import_module", _import_fail)
    with pytest.raises(ImportError, match="Failed to import module"):
        build_legacy_plugin("x.y", registry=registry)

    monkeypatch.setattr(
        "adapters.legacy.registry.importlib.import_module",
        lambda _module_path: SimpleNamespace(),
    )
    with pytest.raises(AttributeError, match="missing callable"):
        build_legacy_plugin("x.y", registry=registry)

    monkeypatch.setattr(
        "adapters.legacy.registry.importlib.import_module",
        lambda _module_path: SimpleNamespace(main=123),
    )
    with pytest.raises(TypeError, match="resolved non-callable"):
        build_legacy_plugin("x.y", registry=registry)


def test_build_legacy_plugin_returns_plugin_on_success(monkeypatch):
    registry = {"x.y": LegacyEntrypointSpec("x.y", "main")}
    monkeypatch.setattr(
        "adapters.legacy.registry.importlib.import_module",
        lambda _module_path: SimpleNamespace(main=lambda: "ok"),
    )

    plugin = build_legacy_plugin("  x.y  ", registry=registry)
    assert isinstance(plugin, LegacyEntrypointPlugin)
    assert plugin.name() == "x.y"
    assert callable(plugin.entrypoint)
