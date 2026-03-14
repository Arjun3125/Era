"""Lightweight Ollama client for embeddings and text generation."""

from __future__ import annotations

from typing import List, Optional
import os
import requests


class OllamaClient:
    def __init__(self, model: str = "mock-embed", base_url: Optional[str] = None, timeout: int = 30) -> None:
        self.model = model
        self.base_url = (base_url or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self.timeout = timeout

    def embed(self, text: str) -> List[float]:
        payload = {"model": self.model, "input": [text]}
        try:
            resp = requests.post(f"{self.base_url}/api/embed", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "embeddings" in data:
                return data["embeddings"][0]
            if isinstance(data, list):
                return data[0]
        except Exception:
            pass

        # Fallback: deterministic small embedding
        return [float(len(text) % 10) / 10.0] * 8

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        system: Optional[str] = None,
    ) -> str:
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout or self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "response" in data:
                return str(data["response"])
            if isinstance(data, dict) and "message" in data:
                return str(data["message"])
        except Exception:
            pass

        return "{}"
