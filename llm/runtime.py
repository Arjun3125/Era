"""Compatibility shim for OllamaRuntime."""
from __future__ import annotations

from persona.ollama_runtime import OllamaRuntime as _PersonaRuntime


class OllamaRuntime(_PersonaRuntime):
    """Alias for persona.ollama_runtime.OllamaRuntime."""

    pass
