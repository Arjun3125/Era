"""Minimal Ollama client helpers for list/chat."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


def _base_url() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def list(timeout: int = 5) -> List[Dict[str, Any]]:
    """Return model list from Ollama, or empty list on failure."""
    try:
        resp = requests.get(f"{_base_url()}/api/tags", timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("models", []) if isinstance(payload, dict) else []
    except Exception:
        return []


def chat(model: str, messages: List[Dict[str, str]], timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Send a chat request to Ollama, return response JSON or None."""
    payload = {"model": model, "messages": messages, "stream": False}
    try:
        resp = requests.post(f"{_base_url()}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None
