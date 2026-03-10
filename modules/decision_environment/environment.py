"""Decision environment wrapper for training loops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .scenario_simulator import ScenarioSimulator, SimulationResult


ScenarioProvider = Callable[[], Dict[str, Any]]


@dataclass
class StepResult:
    outcome: Dict[str, Any]
    reward: float
    done: bool


class DecisionEnvironment:
    def __init__(
        self,
        scenario_provider: ScenarioProvider,
        *,
        simulator: Optional[ScenarioSimulator] = None,
    ) -> None:
        self._scenario_provider = scenario_provider
        self._simulator = simulator or ScenarioSimulator()
        self._current: Optional[Dict[str, Any]] = None

    def reset(self) -> Dict[str, Any]:
        self._current = self._scenario_provider()
        return dict(self._current)

    def step(self, decision: str) -> StepResult:
        if self._current is None:
            raise RuntimeError("Environment not reset.")
        simulation = self._simulator.simulate(self._current, decision)
        self._current = None
        return StepResult(
            outcome=simulation.outcome.__dict__,
            reward=simulation.reward,
            done=True,
        )
