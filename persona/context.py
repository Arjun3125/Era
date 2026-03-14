"""System context builder for Persona."""

from __future__ import annotations

from typing import Dict

from .state import CognitiveState


MODE_VISIBLE_HINT: Dict[str, str] = {
    "quick": "Respond briefly and directly.",
    "war": "Be assertive and decisive.",
    "meeting": "Provide balanced, structured guidance.",
    "darbar": "Use deep deliberation and multiple viewpoints.",
}

MODE_INERTIA: Dict[str, float] = {
    "quick": 0.1,
    "war": 0.3,
    "meeting": 0.5,
    "darbar": 0.8,
}


def build_system_context(state: CognitiveState) -> str:
    mode = state.mode or "meeting"
    hint = MODE_VISIBLE_HINT.get(mode, MODE_VISIBLE_HINT["meeting"])
    domains = ", ".join(state.domains) if state.domains else "general"
    return "\n".join(
        [
            f"Mode: {mode}",
            f"Hint: {hint}",
            f"Domains: {domains}",
            f"Turn: {state.turn_count}",
        ]
    )
