"""Ollama LLM client wrapper and strict JSON helper."""
from __future__ import annotations

import json
import os
import subprocess
import requests
from typing import List, Optional, Any, Dict

from .config import DEFAULT_EXTRACT_MODEL, DEFAULT_DEEPSEEK_MODEL


class OllamaClient:
    """Ollama client supporting fast HTTP API with CLI fallback."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None, timeout: int = 60, cmd: str = "ollama") -> None:
        self.model = model or DEFAULT_EXTRACT_MODEL
        self.base_url = (base_url or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.timeout = timeout
        self.cmd = cmd
        self.nvidia_keys = [
            os.getenv("NVIDIA_API_KEY") or "",
            "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",
            "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",
        ]
        self.nvidia_keys = [k for k in self.nvidia_keys if k and k.startswith("nvapi-")]
        self._key_idx = 0

    def _get_next_nvidia_key(self) -> str:
        if not self.nvidia_keys:
            return ""
        key = self.nvidia_keys[self._key_idx % len(self.nvidia_keys)]
        self._key_idx += 1
        return key

    def _run_cli(self, args: List[str], input_text: Optional[str] = None, timeout: int = 60) -> str:
        inp = input_text.encode("utf-8") if input_text is not None else None
        proc = subprocess.run(
            [self.cmd] + args,
            input=inp,
            capture_output=True,
            text=False,
            timeout=timeout,
        )
        out_b = proc.stdout or b""
        err_b = proc.stderr or b""
        try:
            out = out_b.decode("utf-8")
        except Exception:
            out = out_b.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            try:
                err = err_b.decode("utf-8")
            except Exception:
                err = err_b.decode("utf-8", errors="replace")
            raise RuntimeError(f"ollama command failed: {' '.join(args)}\nstdout={out}\nstderr={err}")
        return out

    def embed(self, text: str, model: Optional[str] = None, timeout: Optional[int] = None) -> List[float]:
        m = model or self.model
        t = timeout or self.timeout
        if self.nvidia_keys:
            key = self._get_next_nvidia_key()
            for nim_model in ("nvidia/nv-embedqa-e5-v5", "baai/bge-m3", "snowflake/arctic-embed-l"):
                try:
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                    payload = {
                        "model": nim_model,
                        "input": [text],
                        "input_type": "passage",
                        "encoding_format": "float"
                    }
                    resp = requests.post("https://integrate.api.nvidia.com/v1/embeddings", json=payload, headers=headers, timeout=t)
                    resp.raise_for_status()
                    data = resp.json()
                    if "data" in data and data["data"]:
                        return [float(x) for x in data["data"][0]["embedding"]]
                except Exception as e:
                    print(f"[NIM EMBED ERROR on {nim_model}] {e}", flush=True)
                    continue

        # Try HTTP first
        try:
            payload = {"model": m, "input": [text]}
            resp = requests.post(f"{self.base_url}/api/embed", json=payload, timeout=t)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "embeddings" in data and data["embeddings"]:
                return [float(x) for x in data["embeddings"][0]]
            if isinstance(data, list) and data:
                return [float(x) for x in data[0]]
        except Exception:
            pass

        # Try CLI fallback
        try:
            out = self._run_cli(["embed", m, "--text", text], timeout=t)
            vec = json.loads(out)
            if isinstance(vec, list):
                return [float(x) for x in vec]
        except Exception:
            pass

        # Deterministic zero-vector fallback
        return [0.0] * 1024

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        system: Optional[str] = None,
    ) -> str:
        m = model or self.model
        t = timeout or self.timeout
        if self.nvidia_keys:
            key = self._get_next_nvidia_key()
            nim_models = ["meta/llama-3.1-8b-instruct", "mistralai/mistral-7b-instruct-v0.3", "meta/llama-3.1-70b-instruct"]
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            for nim_model in nim_models:
                try:
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                    payload = {
                        "model": nim_model,
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 4096
                    }
                    resp = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", json=payload, headers=headers, timeout=t)
                    resp.raise_for_status()
                    data = resp.json()
                    if "choices" in data and data["choices"]:
                        return str(data["choices"][0]["message"]["content"]).strip()
                except Exception as e:
                    print(f"[NIM GENERATE ERROR on {nim_model}] {e}", flush=True)
                    continue

        # Try HTTP first
        try:
            payload = {
                "model": m,
                "prompt": prompt,
                "stream": False,
            }
            if system:
                payload["system"] = system
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=t,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "response" in data:
                return str(data["response"]).strip()
        except Exception:
            pass

        # Try CLI fallback
        try:
            full = (system or "") + "\n\n" + prompt if system else prompt
            return self._run_cli(["run", m, full], timeout=t).strip()
        except Exception:
            pass

        return "{}"


def call_json_llm_strict(
    prompt: str,
    system: str,
    client: OllamaClient,
    timeout: int = 60,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Call LLM and parse JSON object from output."""
    full = (system or "") + "\n\n" + prompt

    # Choose model: explicit override, or deepseek if doctrine-related
    selected_model = model
    if selected_model is None:
        low = (system or "").lower()
        if "doctrine" in low or "deepseek" in low or "doctrine extraction" in low:
            selected_model = DEFAULT_DEEPSEEK_MODEL
        else:
            selected_model = client.model or DEFAULT_EXTRACT_MODEL

    raw = client.generate(full, model=selected_model, timeout=timeout)
    if not raw:
        return {}

    # Try parse entire output
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to extract first JSON object substring
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            if isinstance(obj, dict):
                for k in ("domains", "principles", "rules", "claims", "warnings"):
                    if k not in obj:
                        obj[k] = []
                return obj
        except Exception:
            pass

    # Safe deterministic fallbacks
    lower = (system or "").lower() + "\n" + (prompt or "").lower()
    if "decision" in lower:
        return {"decision": "continue_chapter", "confidence": 0.0}
    if "domains" in lower:
        return {
            "domains": ["strategy"],
            "principles": [{"statement": "Prioritize clear objectives", "abstracted_from": None}],
            "rules": [{"condition": "When uncertain", "action": "Prefer conservative options"}],
            "claims": [],
            "warnings": [],
        }

    return {}
