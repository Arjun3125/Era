"""Compatibility facade over the unified council execution engine."""

from __future__ import annotations

from typing import Any, Dict, List

from modules.council_execution.engine import CouncilExecutionEngine

from .mode_orchestrator import ExecutionConfig


class DynamicCouncil:
    """Backwards-compatible API that delegates to the new council engine."""

    def __init__(self, llm: Any = None, config: ExecutionConfig | None = None):
        self.llm = llm
        self.engine = CouncilExecutionEngine.create(llm=llm, config=config)
        self.mode_orchestrator = self.engine.orchestrator
        self.current_mode = self.mode_orchestrator.get_current_mode()

    @property
    def disabled(self) -> bool:
        return self.engine.disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self.engine.disabled = bool(value)

    @property
    def base_council(self) -> Any:
        """Expose lazy council instance for legacy callers."""
        return self.engine.base_council

    def set_mode(self, mode: str) -> bool:
        updated = self.engine.set_mode(mode)
        self.current_mode = self.engine.get_current_mode()
        return updated

    def convene_for_mode(
        self,
        mode: str,
        user_input: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = self.engine.convene(mode=mode, user_input=user_input, context=context)
        self.current_mode = result.get("mode", self.engine.get_current_mode())
        return result

    def get_current_mode(self) -> str:
        self.current_mode = self.engine.get_current_mode()
        return self.current_mode

    def get_mode_description(self, mode: str) -> str:
        return self.engine.get_mode_description(mode)

    def list_available_modes(self) -> List[str]:
        return self.engine.list_modes()
