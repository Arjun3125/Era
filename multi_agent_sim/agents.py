"""
agents.py
Defines agent wrappers. CloudAgent calls OpenRouter API.
Also includes MockAgent useful for offline tests.
"""
from typing import Callable, Optional


class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def respond(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError()


class CloudAgent(BaseAgent):
    def __init__(self, model: str = "nvidia/nemotron-3-ultra-550b-a55b:free", name: str = "cloud_agent", timeout: Optional[int] = None):
        super().__init__(name)
        self.model = model
        self.timeout = timeout

    def respond(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import os
            os.environ.setdefault("SKIP_OLLAMA_CHECK", "1")
            from persona.openrouter_runtime import OpenRouterRuntime
            llm = OpenRouterRuntime(speak_model=self.model, analyze_model=self.model)
            return llm.speak(system_prompt or "You are a helpful assistant.", user_prompt or "")
        except Exception as e:
            return f"[CLOUD_LLM_ERROR] {e}"


# Backward compat alias
OllamaAgent = CloudAgent


class MockAgent(BaseAgent):
    def __init__(self, behavior_fn: Optional[Callable[[str, str], str]] = None, name: str = "mock"):
        super().__init__(name)
        self.behavior_fn = behavior_fn or (lambda s, u: f"MOCK_RESPONSE to: {u[:80]}")

    def respond(self, system_prompt: str, user_prompt: str) -> str:
        try:
            return self.behavior_fn(system_prompt, user_prompt)
        except Exception as e:
            return f"[MOCK_ERROR] {e}"
