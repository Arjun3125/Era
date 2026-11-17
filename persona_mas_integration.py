"""Persona multi-agent system stub."""

from __future__ import annotations

from dataclasses import dataclass

from persona.openrouter_runtime import OpenRouterRuntime


@dataclass
class PersonaAgent:
    speak_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    analyze_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

    def __post_init__(self) -> None:
        self.llm = OpenRouterRuntime(
            speak_model=self.speak_model,
            analyze_model=self.analyze_model,
        )

    def respond(self, prompt: str) -> str:
        return self.llm.speak("You are Persona.", prompt)


def main() -> int:
    agent = PersonaAgent()
    agent.respond("Hello")
    return 0
