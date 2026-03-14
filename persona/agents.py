"""Simple Persona agent wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from .brain import PersonaBrain
from .ollama_runtime import OllamaRuntime
from .state import CognitiveState
from .context import build_system_context


@dataclass
class SimplePersonaAgent:
    name: str = "persona"
    mode: str = "quick"

    def __post_init__(self) -> None:
        self.state = CognitiveState(mode=self.mode)
        self.brain = PersonaBrain()
        self.llm = OllamaRuntime()

    def respond(self, user_prompt: str) -> str:
        system_prompt = build_system_context(self.state)
        response = self.llm.speak(system_prompt, user_prompt)
        self.state.add_turn(user_prompt, response)
        return response
