"""LLM interaction and interactive conversation modules.

Provides:
- OllamaRuntime: local Ollama CLI wrapper for model calls
- OllamaModelSelector: interactive model picker
- Interactive conversation terminals for USER↔LLM and USER↔Persona
"""
from .ollama import list, chat

__all__ = ["list", "chat"]
