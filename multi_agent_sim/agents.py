"""
agents.py
Defines agent wrappers. OllamaAgent calls `ollama run` via subprocess by default.
Also includes a MockAgent useful for offline tests.
"""
from typing import Callable, Optional
import subprocess
import shlex


class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    def respond(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError()


class OllamaAgent(BaseAgent):
    def __init__(self, model: str, name: str = "ollama_agent", timeout: Optional[int] = None):
        super().__init__(name)
        self.model = model
        self.timeout = timeout

    def _call_ollama(self, prompt: str) -> str:
        # Use subprocess to call ollama run <model>
        try:
            proc = subprocess.run([
                "ollama",
                "run",
                self.model,
            ], input=prompt, text=True, capture_output=True, timeout=self.timeout)
            out = proc.stdout or ""
            return out.strip()
        except Exception as e:
            return f"[OLLAMA_RUN_ERROR] {e}"

    def respond(self, system_prompt: str, user_prompt: str) -> str:
        prompt = (system_prompt or "") + "\n" + (user_prompt or "")
        return self._call_ollama(prompt)


class MockAgent(BaseAgent):
    def __init__(self, behavior_fn: Optional[Callable[[str, str], str]] = None, name: str = "mock"):
        super().__init__(name)
        self.behavior_fn = behavior_fn or (lambda s, u: f"MOCK_RESPONSE to: {u[:80]}")

    def respond(self, system_prompt: str, user_prompt: str) -> str:
        try:
            return self.behavior_fn(system_prompt, user_prompt)
        except Exception as e:
            return f"[MOCK_ERROR] {e}"
