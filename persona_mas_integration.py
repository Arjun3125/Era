"""Persona multi-agent system stub."""

from __future__ import annotations

from dataclasses import dataclass

from persona.ollama_runtime import OllamaRuntime


@dataclass
class PersonaAgent:
    speak_model: str = "llama3.1:8b-instruct-q4_0"
    analyze_model: str = "huihui_ai/deepseek-r1-abliterated:8b"

    def __post_init__(self) -> None:
        self.llm = OllamaRuntime(
            speak_model=self.speak_model,
            analyze_model=self.analyze_model,
        )

    def respond(self, prompt: str) -> str:
        return self.llm.speak("You are Persona.", prompt)


def main() -> int:
    agent = PersonaAgent()
    agent.respond("Hello")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
