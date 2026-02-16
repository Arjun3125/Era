"""Ollama LLM client wrapper."""
import json
from typing import List, Optional, Any, Dict, Union
import os

try:
    import requests
except Exception:
    requests = None

from .config import DEFAULT_EXTRACT_MODEL, DEFAULT_DEEPSEEK_MODEL


class OllamaClient:
    """Ollama client using the local HTTP API at http://localhost:11434.

    Falls back to the CLI only if the HTTP path is not available.
    Uses a persistent `requests.Session` for speed.
    """

    def __init__(self, model: Optional[str] = None, base_url: str = "http://localhost:11434"):
        self.model = model or DEFAULT_EXTRACT_MODEL
        self.base_url = base_url.rstrip("/")
        self._session = None
        if requests:
            self._session = requests.Session()

    def generate(self, prompt: str, model: Optional[str] = None, temperature: Optional[float] = None, timeout: int = 60, system: Optional[str] = None) -> str:
        m = model or self.model
        # Try HTTP API first
        if self._session:
            try:
                payload = {"model": m, "prompt": prompt, "stream": False}
                if system:
                    payload["system"] = system
                resp = self._session.post(f"{self.base_url}/api/generate", json=payload, timeout=timeout)
                resp.raise_for_status()
                # Expecting text / JSON with `response` or raw text
                try:
                    data = resp.json()
                    # Support multiple possible response shapes
                    if isinstance(data, dict):
                        # common key names
                        for k in ("response", "output", "text", "result"):
                            if k in data:
                                return str(data[k])
                        # last resort: dump entire JSON
                        return json.dumps(data)
                    elif isinstance(data, list):
                        return "\n".join(str(x) for x in data)
                except Exception:
                    return resp.text
            except Exception:
                # Fallthrough to CLI fallback below
                pass

        # Fallback: try running CLI (kept for environments without HTTP access)
        try:
            import subprocess

            inp = prompt.encode("utf-8")
            proc = subprocess.run(["ollama", "run", m, prompt], input=inp, capture_output=True, text=False, timeout=timeout)
            out_b = proc.stdout or b""
            try:
                return out_b.decode("utf-8")
            except Exception:
                return out_b.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def embed(self, text: Union[str, List[str]], model: Optional[str] = None, timeout: int = 60) -> Union[List[float], List[List[float]]]:
        """
        Get embedding(s) for a single text or a list of texts.

        Returns a single embedding (list of floats) when given a string, or
        a list of embeddings when given a list of strings.
        """
        m = model or self.model
        # Try HTTP embed endpoint
        if self._session:
            try:
                payload = {"model": m, "input": text}
                resp = self._session.post(f"{self.base_url}/api/embed", json=payload, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                # Ollama returns either {"embedding": [...]} for single input or
                # {"embeddings": [...]} or list for batched responses. Normalize.
                if isinstance(data, dict):
                    if "embeddings" in data:
                        return [[float(x) for x in emb] for emb in data["embeddings"]]
                    if "embedding" in data:
                        return [float(x) for x in data["embedding"]]
                    # Some Ollama versions return {"data": [{"embedding": [...]}, ...]}
                    if "data" in data and isinstance(data["data"], list):
                        out = []
                        for item in data["data"]:
                            if isinstance(item, dict) and "embedding" in item:
                                out.append([float(x) for x in item["embedding"]])
                        if out:
                            return out if isinstance(text, list) else out[0]
                if isinstance(data, list):
                    # assume list of embeddings
                    return [[float(x) for x in item] for item in data]
            except Exception:
                pass

        # Fallback to zero-vector (single or batch)
        if isinstance(text, list):
            return [[0.0] * 768 for _ in text]
        return [0.0] * 768


def call_json_llm_strict(
    prompt: str,
    system: str,
    client: OllamaClient,
    timeout: int = 60,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call LLM and parse JSON object from output.

    Args:
        prompt: User prompt
        system: System prompt
        client: OllamaClient instance
        timeout: Timeout in seconds
        model: Override model selection
        
    Returns:
        Parsed JSON object or safe fallback
    """
    # Choose model: explicit override, or deepseek if doctrine-related
    selected_model = model
    if selected_model is None:
        low = (system or "").lower()
        if "doctrine" in low or "deepseek" in low or "doctrine extraction" in low:
            selected_model = DEFAULT_DEEPSEEK_MODEL
        else:
            selected_model = client.model or DEFAULT_EXTRACT_MODEL

    # Call LLM with separate system and prompt fields
    raw = client.generate(prompt, model=selected_model, timeout=timeout, system=system)
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
                # ensure required doctrine keys are present
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
        # minimal abstracted doctrine (non-empty) as safe default
        return {
            "domains": ["strategy"],
            "principles": [{"statement": "Prioritize clear objectives", "abstracted_from": None}],
            "rules": [{"condition": "When uncertain", "action": "Prefer conservative options"}],
            "claims": [],
            "warnings": [],
        }

    return {}