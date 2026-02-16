"""Simple Ollama LLM adapter used by sovereign flows.

Provides a small adapter API: `generate`, `summarize`, `evaluate_viability`.
Wraps `persona.ollama_runtime.OllamaRuntime` when available, with a safe fallback
for unit tests or when Ollama isn't running.
"""
from typing import Optional, Tuple
from persona.trace import trace


class OllamaAdapter:
    def __init__(self, speak_model: Optional[str] = None, analyze_model: Optional[str] = None):
        try:
            # Import OllamaRuntime lazily to avoid hard dependency at import time
            from persona.ollama_runtime import OllamaRuntime
            # If models are None, OllamaRuntime will use its defaults
            self.runtime = OllamaRuntime(speak_model or "", analyze_model or "")
        except Exception as e:
            trace("llm_adapter_init_error", {"error": str(e)})
            # Fallback: runtime unavailable, use lightweight stubs
            self.runtime = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate free-form text from the LLM.

        Falls back to echo behavior when runtime is unavailable.
        """
        try:
            if self.runtime:
                return self.runtime.speak(system_prompt or "", prompt)
            return f"[LLM stub generate] {prompt[:200]}"
        except Exception as e:
            trace("llm_generate_error", {"error": str(e)})
            return f"[LLM error] {e}"

    def summarize(self, text: str) -> str:
        """Return a short summary of `text` using the analyze model."""
        try:
            if self.runtime:
                system = "Summarize the following text into a concise summary (1-2 sentences)."
                return self.runtime.analyze(system, text)
            return text[:400] + ("..." if len(text) > 400 else "")
        except Exception as e:
            trace("llm_summarize_error", {"error": str(e)})
            return f"[LLM summarize error] {e}"

    def evaluate_viability(self, synthesis_text: str) -> Tuple[float, str]:
        """Return a (score 0.0-1.0, reason) tuple evaluating viability.

        This sends a short prompt to the analyze model asking for a numeric score
        and a brief justification. Falls back to a heuristic score when offline.
        """
        try:
            if self.runtime:
                system = (
                    "You are an objective evaluator. Given the synthesis text, return a compact"
                    " JSON object with fields: {\"score\": float (0.0-1.0), \"reason\": string}."
                )
                resp = self.runtime.analyze(system, synthesis_text)
                # Expecting JSON-like; try simple parse
                import json
                try:
                    parsed = json.loads(resp)
                    score = float(parsed.get("score", 0.0))
                    reason = parsed.get("reason", "")
                    return max(0.0, min(1.0, score)), reason
                except Exception:
                    # Not JSON — attempt to extract a float
                    # Look for a leading number
                    import re
                    m = re.search(r"([0-9]*\.?[0-9]+)", resp)
                    if m:
                        score = float(m.group(1))
                        return max(0.0, min(1.0, score)), resp
                    return 0.0, resp

            # Fallback heuristic: neutral
            return 0.5, "fallback heuristic (LLM unavailable)"
        except Exception as e:
            trace("llm_evaluate_viability_error", {"error": str(e)})
            return 0.0, str(e)

    # Compatibility shims for persona runtime which expects OllamaRuntime-like API
    def speak(self, system_context: str, user_input: str) -> str:
        return self.generate(user_input, system_context)

    def analyze(self, system_prompt: str, user_prompt: str) -> str:
        try:
            if self.runtime:
                return self.runtime.analyze(system_prompt, user_prompt)
            # simple heuristic: return a short JSON-ish string
            return '{"result": "analyzed", "text": "%s"}' % (user_prompt[:200].replace('"', "'"))
        except Exception as e:
            trace("llm_analyze_error", {"error": str(e)})
            return f"[LLM analyze error] {e}"

    def analyze_async(self, system_prompt: str, user_prompt: str):
        try:
            if self.runtime:
                return self.runtime.analyze_async(system_prompt, user_prompt)
            # fallback: return a completed Future-like object via concurrency
            from concurrent.futures import ThreadPoolExecutor
            executor = ThreadPoolExecutor(max_workers=1)
            return executor.submit(lambda: self.analyze(system_prompt, user_prompt))
        except Exception as e:
            trace("llm_analyze_async_error", {"error": str(e)})
            raise

    def speak_async(self, system_context: str, user_input: str):
        try:
            if self.runtime:
                return self.runtime.speak_async(system_context, user_input)
            from concurrent.futures import ThreadPoolExecutor
            executor = ThreadPoolExecutor(max_workers=1)
            return executor.submit(lambda: self.speak(system_context, user_input))
        except Exception as e:
            trace("llm_speak_async_error", {"error": str(e)})
            raise
