"""LLM interaction utilities used by refactored entrypoints."""

from .ollama import list, chat
from .runtime import OllamaRuntime

try:  # Optional: ingestion-specific client
    from ingestion.v2.src.ollama_client import OllamaClient  # type: ignore
except Exception:  # pragma: no cover - fallback for minimal installs
    try:
        from ingestion.v1.llm import OllamaClient  # type: ignore
    except Exception:
        OllamaClient = None  # type: ignore

__all__ = ["list", "chat", "OllamaRuntime", "OllamaClient"]
