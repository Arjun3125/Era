"""Legacy Persona compatibility layer for test suites."""

from .state import CognitiveState
from .brain import ControlDirective, PersonaBrain
from .context import build_system_context, MODE_VISIBLE_HINT, MODE_INERTIA
from .knowledge_engine import synthesize_knowledge
from .opencode_runtime import OpenCodeRuntime
from .openrouter_runtime import OpenRouterRuntime

__all__ = [
    "CognitiveState",
    "ControlDirective",
    "PersonaBrain",
    "build_system_context",
    "MODE_VISIBLE_HINT",
    "MODE_INERTIA",
    "synthesize_knowledge",
    "OpenCodeRuntime",
    "OpenRouterRuntime",
]
