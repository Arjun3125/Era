"""Adapters that wrap existing entrypoints behind the new orchestrator contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Sequence
import time

from core.contracts.context import ExecutionContext
from core.contracts.module import ModuleHealth, ModulePlugin, ModuleResult, ModuleStatus
from core.orchestrator.runtime import StageOutcome


@dataclass
class LegacyEntrypointPlugin(ModulePlugin):
    """Thin plugin wrapper around a callable legacy entrypoint."""

    plugin_name: str
    entrypoint: Callable[..., Any]
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.plugin_name = self._normalize_plugin_name(self.plugin_name)
        self.args = self._normalize_args(self.args)
        self.kwargs = self._normalize_kwargs(self.kwargs)

    def name(self) -> str:
        return self.plugin_name

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "type": "legacy_entrypoint",
            "blocking": True,
            "stage_safe": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError("LegacyEntrypointPlugin requires an ExecutionContext.")
        if not callable(self.entrypoint):
            raise TypeError(f"Entrypoint for plugin '{self.plugin_name}' is not callable.")

    def execute(self, context: ExecutionContext) -> ModuleResult:
        self.validate(context)
        started = time.perf_counter()

        try:
            value = self.entrypoint(*self.args, **self.kwargs)
        except SystemExit as exc:
            normalized_code = self._coerce_exit_code(exc.code, default=1)
            status = ModuleStatus.SUCCESS if normalized_code == 0 else ModuleStatus.FAILED
            errors = [] if status == ModuleStatus.SUCCESS else [f"SystemExit({normalized_code})"]
            return ModuleResult(
                status=status,
                outputs={
                    "legacy_plugin": self.plugin_name,
                    "legacy_exit_code": normalized_code,
                },
                metrics={
                    "duration_ms": self._duration_ms(started)
                },
                errors=errors,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            return ModuleResult(
                status=ModuleStatus.FAILED,
                outputs={
                    "legacy_plugin": self.plugin_name,
                    "legacy_exit_code": 1,
                },
                metrics={
                    "duration_ms": self._duration_ms(started)
                },
                errors=[f"{type(exc).__name__}: {exc}"],
            )

        return ModuleResult(
            status=ModuleStatus.SUCCESS,
            outputs={
                "legacy_plugin": self.plugin_name,
                "legacy_result": value,
                "legacy_exit_code": 0,
            },
            metrics={"duration_ms": self._duration_ms(started)},
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(
            ok=callable(self.entrypoint),
            details={
                "plugin_name": self.plugin_name,
                "callable": callable(self.entrypoint),
                "arg_count": len(self.args),
                "kwarg_count": len(self.kwargs),
            },
        )

    @staticmethod
    def _normalize_plugin_name(value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise ValueError("Legacy entrypoint plugin name must be non-empty.")
        return name

    @staticmethod
    def _normalize_args(value: Any) -> tuple[Any, ...]:
        if value is None:
            return ()
        if isinstance(value, tuple):
            return value
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return tuple(value)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, Mapping)):
            try:
                return tuple(list(value))
            except Exception:
                raise TypeError("Legacy entrypoint args must be a sequence when provided.")
        raise TypeError("Legacy entrypoint args must be a sequence when provided.")

    @staticmethod
    def _normalize_kwargs(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return {
                LegacyEntrypointPlugin._normalize_mapping_key(key): item
                for key, item in dict(value).items()
            }
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            try:
                pairs = list(value)
            except Exception:
                raise TypeError("Legacy entrypoint kwargs must be a mapping when provided.")
            normalized: Dict[str, Any] = {}
            for item in pairs:
                if isinstance(item, Mapping):
                    raise TypeError("Legacy entrypoint kwargs must be a mapping when provided.")
                try:
                    key, item_value = item
                except Exception:
                    raise TypeError("Legacy entrypoint kwargs must be a mapping when provided.")
                normalized[LegacyEntrypointPlugin._normalize_mapping_key(key)] = item_value
            return normalized
        raise TypeError("Legacy entrypoint kwargs must be a mapping when provided.")

    @staticmethod
    def _normalize_mapping_key(value: Any) -> str:
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace")
        return str(value)

    @staticmethod
    def _duration_ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000.0, 3)

    @staticmethod
    def _coerce_exit_code(value: Any, *, default: int) -> int:
        if value is None:
            return default
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return value
        text = str(value).strip()
        if not text:
            return default
        try:
            return int(text)
        except Exception:
            return default


def plugin_stage_handler(plugin: ModulePlugin) -> Callable[[ExecutionContext], StageOutcome]:
    """Build a runtime stage handler from a plugin implementation."""
    if not hasattr(plugin, "validate") or not callable(getattr(plugin, "validate")):
        raise TypeError("Plugin must define callable 'validate(context)'.")
    if not hasattr(plugin, "execute") or not callable(getattr(plugin, "execute")):
        raise TypeError("Plugin must define callable 'execute(context)'.")

    def _handler(context: ExecutionContext) -> StageOutcome:
        plugin.validate(context)
        result = plugin.execute(context)
        if not isinstance(result, ModuleResult):
            raise TypeError("Plugin execute() must return ModuleResult.")

        outputs = dict(result.outputs or {})
        errors = list(result.errors or [])

        if result.status == ModuleStatus.FAILED:
            return StageOutcome(
                outputs=outputs,
                errors=errors,
                continue_pipeline=False,
                degraded=False,
            )

        if result.status == ModuleStatus.DEGRADED:
            return StageOutcome(
                outputs=outputs,
                errors=errors,
                continue_pipeline=True,
                degraded=True,
            )

        if errors:
            return StageOutcome(
                outputs=outputs,
                errors=errors,
                continue_pipeline=True,
                degraded=True,
            )
        return StageOutcome(outputs=outputs, continue_pipeline=True)

    return _handler
