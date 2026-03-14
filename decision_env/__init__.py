"""Embedded decision environment for scenario-based ERA policy evaluation."""

from .environment import DecisionEnvironment, MultiStepDecisionEnvironment, LongHorizonDecisionEnvironment
from .episode_runner import (
    EpisodeRecord,
    EpisodeRunner,
    EraDecisionAgent,
    MultiStepEpisodeRecord,
    MultiStepEpisodeRunner,
    MultiStepTrainingSummary,
    LongHorizonEpisodeRecord,
    LongHorizonEpisodeRunner,
    PolicyEvaluation,
    TrainingLoopSummary,
)
from .reward_function import RewardBreakdown, RewardFunction
from .reward_model import RewardModel, RewardSignal, delayed_reward
from .scenario_generator import (
    SCENARIO_DOMAINS,
    DecisionScenario,
    ScenarioGenerator,
    ScenarioOption,
)
from .simulator import OutcomeSimulator, SimulationOutcome
from .state_model import DecisionState, LongHorizonState, StateTransition
from .transition_model import TransitionModel

__all__ = (
    "DecisionEnvironment",
    "MultiStepDecisionEnvironment",
    "LongHorizonDecisionEnvironment",
    "DecisionScenario",
    "EpisodeRecord",
    "EpisodeRunner",
    "EraDecisionAgent",
    "MultiStepEpisodeRecord",
    "MultiStepEpisodeRunner",
    "MultiStepTrainingSummary",
    "LongHorizonEpisodeRecord",
    "LongHorizonEpisodeRunner",
    "OutcomeSimulator",
    "PolicyEvaluation",
    "RewardBreakdown",
    "RewardFunction",
    "RewardModel",
    "RewardSignal",
    "delayed_reward",
    "SCENARIO_DOMAINS",
    "ScenarioGenerator",
    "ScenarioOption",
    "SimulationOutcome",
    "DecisionState",
    "LongHorizonState",
    "StateTransition",
    "TransitionModel",
    "TrainingLoopSummary",
)
