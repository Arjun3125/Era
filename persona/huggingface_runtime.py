"""
HuggingFaceRuntime — fallback cloud LLM adapter using HuggingFace Inference Providers.

Uses HF's OpenAI-compatible endpoint at router.huggingface.co/v1.
Free tier: few hundred requests per hour.

Set env vars:
  HUGGINGFACE_HF_TOKEN=hf_...  (optional, increases rate limits)
  HF_SPEAK_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct  (optional)
  HF_ANALYZE_MODEL=Qwen/Qwen2.5-7B-Instruct  (optional)

Usage:
  from persona.huggingface_runtime import HuggingFaceRuntime
  llm = HuggingFaceRuntime()
  response = llm.speak("You are a minister.", "What should I do?")
"""

import os
import time
import json
import urllib.request
import urllib.error

HF_ENDPOINT = "https://router.huggingface.co/v1/chat/completions"

# Good free models available on HF Inference Providers
HF_MODELS = [
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "google/gemma-2-2b-it",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
]

DEFAULT_HF_SPEAK = "meta-llama/Meta-Llama-3.1-8B-Instruct"
DEFAULT_HF_ANALYZE = "Qwen/Qwen2.5-7B-Instruct"


class HuggingFaceRuntime:
    def __init__(self, speak_model=None, analyze_model=None):
        self.hf_token = os.getenv("HUGGINGFACE_HF_TOKEN", os.getenv("HF_TOKEN", ""))
        self.speak_model = speak_model or os.getenv("HF_SPEAK_MODEL", DEFAULT_HF_SPEAK)
        self.analyze_model = analyze_model or os.getenv("HF_ANALYZE_MODEL", DEFAULT_HF_ANALYZE)
        self.messages = []
        self.max_pairs = 10

    def _call_hf(self, model, messages, temperature=0.0, top_p=1.0, max_tokens=2048):
        """Call HuggingFace Inference Providers with fallback models."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"

        models_to_try = [model] + [m for m in HF_MODELS if m != model]

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

                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    HF_ENDPOINT,
                    data=data,
                    headers=headers,
                    method="POST",
                )

                try:
                    with urllib.request.urlopen(req, timeout=90) as resp:
                        result = json.loads(resp.read().decode("utf-8"))
                        choices = result.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            if content.strip():
                                return content.strip()
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
                    raise RuntimeError(f"HF API error {e.code}: {body}")
                except Exception as e:
                    if retry < max_retries - 1:
                        time.sleep(1.0 * (retry + 1))
                        continue
                    break  # try next model

        return ""

    def analyze(self, system_prompt, user_prompt):
        """Silent analysis handshake."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return self._call_hf(self.analyze_model, messages, temperature=0.0)
        except Exception as e:
            return f"[HF analyze error: {e}]"

    def analyze_async(self, system_prompt, user_prompt):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(self.analyze, system_prompt, user_prompt)

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
            assistant_text = self._call_hf(
                self.speak_model,
                self.messages,
                temperature=0.0,
            )
        except Exception as e:
            assistant_text = f"[HF speak error: {e}]"

        self.messages.append({"role": "assistant", "content": assistant_text})
        if len(self.messages) > max_msgs:
            tail = self.messages[-(max_msgs - 1):]
            self.messages = [self.messages[0]] + tail

        return assistant_text

    def speak_async(self, system_context, user_input):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(self.speak, system_context, user_input)
