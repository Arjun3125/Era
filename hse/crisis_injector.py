"""Crisis injection for synthetic human simulations."""
from __future__ import annotations

import random
from typing import Any, Dict, Optional


class CrisisInjector:
    """Injects stochastic crisis events with a simple cooldown."""

    def __init__(self, seed: Optional[int] = None, *, base_rate: float = 0.12, cooldown: int = 3):
        self.rng = random.Random(seed)
        self.base_rate = float(base_rate)
        self.cooldown = int(cooldown)
        self._last_turn: Optional[int] = None

    def maybe_inject(self, human_id: str, human: Any, turn: int) -> Optional[Dict[str, Any]]:
        """Return a crisis event dict or None."""
        if self._last_turn is not None and (turn - self._last_turn) < self.cooldown:
            return None

        roll = self.rng.random()
        if roll > self.base_rate:
            return None

        crisis = self._sample_crisis(human_id, human, roll)
        self._last_turn = turn
        return crisis

    def _sample_crisis(self, human_id: str, human: Any, roll: float) -> Dict[str, Any]:
        crisis_types = [
            ("health", "Unexpected health issue"),
            ("financial", "Sudden expense or cash shortfall"),
            ("relationship", "Conflict with a close relationship"),
            ("career", "Job instability or role uncertainty"),
        ]
        idx = int(roll * len(crisis_types)) % len(crisis_types)
        kind, summary = crisis_types[idx]
        return {
            "human_id": human_id,
            "type": kind,
            "summary": summary,
            "severity": round(0.3 + 0.6 * roll, 2),
        }
