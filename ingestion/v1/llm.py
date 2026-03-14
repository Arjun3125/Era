"""Legacy v1 LLM client stub."""

from __future__ import annotations

import sys
import types

DEFAULT_EXTRACT_MODEL = "mock-extract"


class OllamaClient:
    def __init__(self, model: str = DEFAULT_EXTRACT_MODEL) -> None:
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.0, timeout: int = 60, **_kwargs) -> str:
        return '{"decision": "continue_chapter", "confidence": 0.5}'


# Allow "llm.ollama_model_selector" imports even when this module is on sys.path
__path__ = []  # type: ignore[attr-defined]


def select_models(*_args, **_kwargs):
    return [DEFAULT_EXTRACT_MODEL]


_selector = types.ModuleType("llm.ollama_model_selector")
_selector.select_models = select_models
sys.modules.setdefault("llm.ollama_model_selector", _selector)
