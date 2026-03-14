"""Legacy Persona compatibility layer for test suites."""

from .state import CognitiveState
from .brain import ControlDirective, PersonaBrain
from .context import build_system_context, MODE_VISIBLE_HINT, MODE_INERTIA
from .knowledge_engine import synthesize_knowledge
from .ollama_runtime import OllamaRuntime

__all__ = [
    "CognitiveState",
    "ControlDirective",
    "PersonaBrain",
    "build_system_context",
    "MODE_VISIBLE_HINT",
    "MODE_INERTIA",
    "synthesize_knowledge",
    "OllamaRuntime",
]
