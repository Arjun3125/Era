"""Population management for synthetic humans."""
from __future__ import annotations

from typing import List, Optional

from .human_profile import SyntheticHuman
from .personality_drift import PersonalityDrift


class PopulationManager:
    """Create and manage cohorts of SyntheticHuman instances."""

    def __init__(self, seed: Optional[int] = None):
        self._population: List[SyntheticHuman] = []
        self._drift = PersonalityDrift(seed=seed)
        self._seed = seed

    def create_population(self, count: int) -> List[SyntheticHuman]:
        """Create a cohort of humans with deterministic names if seeded."""
        base_seed = self._seed or 0
        for i in range(int(count)):
            human = SyntheticHuman(name=f"Human_{i+1}", seed=base_seed + i)
            self._population.append(human)
        return list(self._population)

    def add(self, human: SyntheticHuman) -> None:
        self._population.append(human)

    def list(self) -> List[SyntheticHuman]:
        return list(self._population)

    def apply_drift(self, signals) -> None:
        """Apply drift across the population."""
        for human in self._population:
            self._drift.apply(human, signals)
