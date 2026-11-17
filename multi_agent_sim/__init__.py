"""Multi-agent LLM simulation package.
Provides a safe orchestrator to run closed-loop simulations between two LLM agents.

Entry points:
  - Orchestrator: class-based closed-loop agent orchestrator
  - CloudAgent, MockAgent: agent implementations
"""
from .orchestrator import Orchestrator
from .agents import CloudAgent, OllamaAgent, MockAgent
from .archetypes import USER_ARCHETYPES
from .logger import ConversationLogger

__all__ = ["Orchestrator", "CloudAgent", "OllamaAgent", "MockAgent", "USER_ARCHETYPES", "ConversationLogger"]
