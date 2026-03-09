"""Native Ollama runtime for refactored entrypoints."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from . import ollama as ollama_cli

try:  # pragma: no cover - optional dependency
    import ollama as ollama_pkg  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ollama_pkg = None

_EXECUTOR = ThreadPoolExecutor(max_workers=4)


class OllamaRuntime:
    """Minimal, deterministic runtime for speak/analyze calls."""

    def __init__(self, speak_model: str | None = None, analyze_model: str | None = None, global_seed: int | None = None):
        self.speak_model = speak_model or os.getenv("USER_MODEL", "llama3.1:8b-instruct-q4_0")
        self.analyze_model = analyze_model or os.getenv("PROGRAM_MODEL", "huihui_ai/deepseek-r1-abliterated:8b")
        self.global_seed = global_seed or _safe_int(os.getenv("EVAL_SEED"))
        self.messages: List[Dict[str, str]] = []
        self.max_pairs = 10

        self.eval_temperature = 0.0
        self.eval_top_p = 1.0
        self.eval_num_predict = _safe_int(os.getenv("EVAL_NUM_PREDICT"))
        self.fail_fast_errors = os.getenv("EVAL_FAIL_FAST_ERRORS", "0").lower() in {"1", "true", "yes"}
        self.eval_think_off = os.getenv("EVAL_THINK_OFF", "1").lower() in {"1", "true", "yes"}

        skip_check = os.getenv("SKIP_OLLAMA_CHECK", "").lower() in {"1", "true", "yes"}
        if not skip_check:
            self._check_ollama()

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": str(system_prompt or "")},
            {"role": "user", "content": str(user_prompt or "")},
        ]
        try:
            return self._chat(model=self.analyze_model, messages=messages)
        except Exception as exc:
            if self.fail_fast_errors:
                raise RuntimeError(f"Ollama analyze() failed: {exc}") from exc
            return f"[LLM analyze error: {exc}]"

    def analyze_async(self, system_prompt: str, user_prompt: str):
        return _EXECUTOR.submit(self.analyze, system_prompt, user_prompt)

    def speak(self, system_context: str, user_input: str) -> str:
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = str(system_context or "")
        else:
            self.messages.insert(0, {"role": "system", "content": str(system_context or "")})

        self.messages.append({"role": "user", "content": str(user_input or "")})
        self._trim_messages()

        try:
            assistant_text = self._chat(model=self.speak_model, messages=list(self.messages))
        except Exception as exc:
            if self.fail_fast_errors:
                raise RuntimeError(f"Ollama speak() failed: {exc}") from exc
            assistant_text = f"[LLM speak error: {exc}]"

        self.messages.append({"role": "assistant", "content": assistant_text})
        self._trim_messages()
        return assistant_text

    def speak_async(self, system_context: str, user_input: str):
        return _EXECUTOR.submit(self.speak, system_context, user_input)

    def _chat(self, *, model: str, messages: List[Dict[str, str]]) -> str:
        if ollama_pkg is not None:  # pragma: no branch
            options: Dict[str, Any] = {
                "temperature": self.eval_temperature,
                "top_p": self.eval_top_p,
            }
            if self.global_seed is not None:
                options["seed"] = int(self.global_seed)
            if self.eval_num_predict is not None:
                options["num_predict"] = int(self.eval_num_predict)

            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "options": options,
            }
            if self.eval_think_off:
                kwargs["think"] = False
            response = ollama_pkg.chat(**kwargs)
            payload = response.model_dump() if hasattr(response, "model_dump") else response
            message = payload.get("message", {}) if isinstance(payload, dict) else {}
            content = str(message.get("content") or "").strip()
            if content:
                return content
            thinking = str(message.get("thinking") or "").strip()
            return thinking

        response = ollama_cli.chat(model=model, messages=messages)
        message = response.get("message", {}) if isinstance(response, dict) else {}
        return str(message.get("content") or "").strip()

    def _check_ollama(self) -> None:
        if ollama_pkg is not None:  # pragma: no branch
            ollama_pkg.list()
            return
        ollama_cli.list()

    def _trim_messages(self) -> None:
        max_msgs = 1 + (self.max_pairs * 2)
        if len(self.messages) <= max_msgs:
            return
        tail = self.messages[-(max_msgs - 1):]
        self.messages = [self.messages[0]] + tail


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except Exception:
        return None
