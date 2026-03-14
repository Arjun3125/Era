"""Minimal archetype definitions for multi-agent simulations."""

USER_ARCHETYPES = [
    {
        "name": "curious_explorer",
        "description": "Asks exploratory questions and seeks clarification.",
        "tone": "curious",
    },
    {
        "name": "skeptical_operator",
        "description": "Challenges assumptions and asks for evidence.",
        "tone": "skeptical",
    },
    {
        "name": "decisive_leader",
        "description": "Wants concise, actionable guidance with tradeoffs.",
        "tone": "direct",
    },
]

__all__ = ["USER_ARCHETYPES"]
