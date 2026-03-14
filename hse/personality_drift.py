"""Personality drift model for synthetic humans."""
from __future__ import annotations

import random
from typing import Any, Dict, Optional


class PersonalityDrift:
    """Applies small stochastic drift to trait vectors based on signals."""

    def __init__(self, seed: Optional[int] = None, *, max_step: float = 0.05):
        self.rng = random.Random(seed)
        self.max_step = float(max_step)

    def apply(self, human: Any, signals: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Mutate the human traits in-place and return a drift record."""
        signals = signals or {}
        traits = getattr(human, "traits", {}) or {}
        if not traits:
            return {"updated": False, "reason": "no_traits"}

        stress = float(signals.get("stress", 0.0))
        success = float(signals.get("success_rate", 0.0))
        repetition = float(signals.get("repetition", 0.0))

        drift_record = {}
        for trait, value in traits.items():
            # Stress nudges impulsive traits up, success nudges stability up.
            direction = (success - stress) + (self.rng.random() - 0.5) * 0.2
            step = max(-self.max_step, min(self.max_step, direction * (0.02 + repetition * 0.01)))
            new_value = max(0.0, min(1.0, float(value) + step))
            traits[trait] = new_value
            drift_record[trait] = {"old": value, "new": new_value, "step": step}

        human.traits = traits
        return {"updated": True, "traits": drift_record}
