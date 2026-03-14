"""Minimal ML-integrated conversation stub."""

from __future__ import annotations

from persona.ollama_runtime import OllamaRuntime


class MLIntegratedConversation:
    def __init__(self) -> None:
        self.llm = OllamaRuntime()

    def run(self, prompt: str) -> str:
        return self.llm.speak("You are a helper.", prompt)
