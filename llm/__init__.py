"""LLM interaction utilities used by refactored entrypoints."""

from persona.openrouter_runtime import OpenRouterRuntime

try:  # Optional: ingestion-specific client
    from ingestion.v2.src.ollama_client import OllamaClient  # type: ignore
except Exception:  # pragma: no cover - fallback for minimal installs
    try:
        from ingestion.v1.llm import OllamaClient  # type: ignore
    except Exception:
        OllamaClient = None  # type: ignore

__all__ = ["OpenRouterRuntime", "OllamaClient"]
