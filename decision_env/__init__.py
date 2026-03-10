"""Embedded decision environment for scenario-based ERA policy evaluation."""

from .environment import DecisionEnvironment
from .episode_runner import (
    EpisodeRecord,
    EpisodeRunner,
    EraDecisionAgent,
    PolicyEvaluation,
    TrainingLoopSummary,
)
from .reward_function import RewardBreakdown, RewardFunction
from .scenario_generator import (
    SCENARIO_DOMAINS,
    DecisionScenario,
    ScenarioGenerator,
    ScenarioOption,
)
from .simulator import OutcomeSimulator, SimulationOutcome

__all__ = (
    "DecisionEnvironment",
    "DecisionScenario",
    "EpisodeRecord",
    "EpisodeRunner",
    "EraDecisionAgent",
    "OutcomeSimulator",
    "PolicyEvaluation",
    "RewardBreakdown",
    "RewardFunction",
    "SCENARIO_DOMAINS",
    "ScenarioGenerator",
    "ScenarioOption",
    "SimulationOutcome",
    "TrainingLoopSummary",
)
