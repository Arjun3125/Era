"""Minimal ML-integrated conversation stub."""

from __future__ import annotations

from persona.openrouter_runtime import OpenRouterRuntime


class MLIntegratedConversation:
    def __init__(self) -> None:
        self.llm = OpenRouterRuntime()

    def run(self, prompt: str) -> str:
        return self.llm.speak("You are a helper.", prompt)
