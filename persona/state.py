"""Lightweight CognitiveState for legacy Persona tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class CognitiveState:
    mode: str = "quick"
    turn_count: int = 0
    domains: List[str] = field(default_factory=list)
    domain_confidence: float = 0.0
    emotional_metrics: Dict[str, Any] = field(default_factory=dict)
    recent_turns: List[Tuple[str, str]] = field(default_factory=list)
    background_knowledge: List[str] = field(default_factory=list)
    last_situation: Dict[str, Any] = field(default_factory=dict)
    last_mode_eval: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, user_input: str, response: str) -> None:
        self.turn_count += 1
        self.recent_turns.append((str(user_input), str(response)))
        if len(self.recent_turns) > 50:
            self.recent_turns = self.recent_turns[-50:]

    def update_domains(self, domains: List[str], confidence: float) -> None:
        self.domains = [str(item) for item in domains]
        self.domain_confidence = float(confidence)

    def get_recent_context(self, limit: int = 5) -> str:
        tail = self.recent_turns[-limit:]
        return "\n".join(f"User: {u}\nAssistant: {r}" for u, r in tail)

    def reset_for_new_conversation(self) -> None:
        self.turn_count = 0
        self.domains = []
        self.domain_confidence = 0.0
        self.emotional_metrics = {}
        self.recent_turns = []
        self.last_situation = {}
        self.last_mode_eval = {}
