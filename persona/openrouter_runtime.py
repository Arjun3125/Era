"""
OpenRouterRuntime — cloud LLM adapter for ERA using OpenRouter's OpenAI-compatible API.

Set env vars:
  OPENROUTER_API_KEY=sk-or-...  (required)
  OPENROUTER_SPEAK_MODEL=meta-llama/llama-3.1-8b-instruct:free  (optional, has default)
  OPENROUTER_ANALYZE_MODEL=meta-llama/llama-3.1-8b-instruct:free  (optional, has default)

Usage:
  from persona.openrouter_runtime import OpenRouterRuntime
  llm = OpenRouterRuntime()
  response = llm.speak("You are a minister.", "What should I do?")
"""

import os
import time
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

# Free models on OpenRouter (as of 2026)
FREE_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nousresearch/hermes-3-llama-3.1-8b:free",
]

DEFAULT_SPEAK = "nvidia/nemotron-3.5-lightning:free"
DEFAULT_ANALYZE = "nvidia/nemotron-3.5-lightning:free"


class OpenRouterRuntime:
    def __init__(self, speak_model=None, analyze_model=None, global_seed=None):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. Get a free key at https://openrouter.ai/keys\n"
                "Then: $env:OPENROUTER_API_KEY='sk-or-...'"
            )

        self.speak_model = speak_model or os.getenv("OPENROUTER_SPEAK_MODEL", DEFAULT_SPEAK)
        self.analyze_model = analyze_model or os.getenv("OPENROUTER_ANALYZE_MODEL", DEFAULT_ANALYZE)
        self.global_seed = global_seed or os.getenv("EVAL_SEED", None)
        self.messages = []
        self.max_pairs = 10

        self.eval_temperature = 0.0
        self.eval_top_p = 1.0
        self.eval_num_predict = os.getenv("EVAL_NUM_PREDICT", None)
        self.eval_think_off = os.getenv("EVAL_THINK_OFF", "1").lower() in {"1", "true", "yes"}
        self.fail_fast_errors = os.getenv("EVAL_FAIL_FAST_ERRORS", "0").lower() in {"1", "true", "yes"}

        # HuggingFace fallback (lazy-loaded)
        self._hf_runtime = None
        self._hf_enabled = os.getenv("HF_FALLBACK", "1").lower() in {"1", "true", "yes"}

    def _get_hf_runtime(self):
        """Lazy-load HuggingFace fallback runtime."""
        if self._hf_runtime is None and self._hf_enabled:
            try:
                from persona.huggingface_runtime import HuggingFaceRuntime
                self._hf_runtime = HuggingFaceRuntime()
            except Exception:
                self._hf_enabled = False
        return self._hf_runtime

    def _call_openrouter(self, model, messages, temperature=0.0, top_p=1.0, max_tokens=2048):
        """Call OpenRouter API with retry and model fallback."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        fallback_models = [
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-4-31b-it:free",
            "qwen/qwen-2.5-7b-instruct:free",
        ]
        models_to_try = [model] + [m for m in fallback_models if m != model]

        for attempt, current_model in enumerate(models_to_try):
            max_retries = 2 if attempt == 0 else 1
            for retry in range(max_retries):
                payload = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                }
                if self.global_seed is not None:
                    payload["seed"] = int(self.global_seed)

                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/era-project",
                        "X-Title": "ERA Darbar",
                    },
                    method="POST",
                )

                try:
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        result = json.loads(resp.read().decode("utf-8"))
                        choices = result.get("choices", [])
                        if choices:
                            msg = choices[0].get("message", {})
                            content = msg.get("content") or ""
                            # Reasoning models may put answer in reasoning_content
                            if not content.strip():
                                content = msg.get("reasoning_content") or ""
                            if content.strip():
                                return content.strip()
                    # Empty response — retry on same model
                    if retry < max_retries - 1:
                        time.sleep(1.0 * (retry + 1))
                        continue
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8", errors="replace")
                    if e.code in (429, 502, 503) and retry < max_retries - 1:
                        time.sleep(2.0 * (retry + 1))
                        continue
                    if e.code in (429, 502, 503):
                        break  # try next model
                    raise RuntimeError(f"OpenRouter API error {e.code}: {body}")
                except Exception as e:
                    if retry < max_retries - 1:
                        time.sleep(1.0 * (retry + 1))
                        continue
                    break  # try next model

        # All OpenRouter models exhausted — try HuggingFace fallback
        hf = self._get_hf_runtime()
        if hf is not None:
            try:
                result = hf._call_hf(hf.speak_model, messages, temperature=temperature, top_p=top_p, max_tokens=max_tokens)
                if result:
                    return result
            except Exception:
                pass

        return ""

    def analyze(self, system_prompt, user_prompt):
        """Silent analysis handshake."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return self._call_openrouter(
                self.analyze_model,
                messages,
                temperature=self.eval_temperature,
                top_p=self.eval_top_p,
            )
        except Exception as e:
            if self.fail_fast_errors:
                raise RuntimeError(f"OpenRouter analyze() failed: {e}") from e
            return f"[LLM analyze error: {e}]"

    def analyze_async(self, system_prompt, user_prompt):
        return executor.submit(self.analyze, system_prompt, user_prompt)

    def speak(self, system_context, user_input):
        """Primary speak handshake — user-visible. Blocking."""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = system_context
        else:
            self.messages.insert(0, {"role": "system", "content": system_context})
        self.messages.append({"role": "user", "content": user_input})

        max_msgs = 1 + (self.max_pairs * 2)
        if len(self.messages) > max_msgs:
            tail = self.messages[-(max_msgs - 1):]
            self.messages = [self.messages[0]] + tail

        try:
            assistant_text = self._call_openrouter(
                self.speak_model,
                self.messages,
                temperature=self.eval_temperature,
                top_p=self.eval_top_p,
            )
        except Exception as e:
            if self.fail_fast_errors:
                raise RuntimeError(f"OpenRouter speak() failed: {e}") from e
            assistant_text = f"[LLM speak error: {e}]"

        self.messages.append({"role": "assistant", "content": assistant_text})
        if len(self.messages) > max_msgs:
            tail = self.messages[-(max_msgs - 1):]
            self.messages = [self.messages[0]] + tail

        return assistant_text

    def speak_async(self, system_context, user_input):
        return executor.submit(self.speak, system_context, user_input)
