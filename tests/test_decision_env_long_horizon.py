from __future__ import annotations

from decision_env import LongHorizonDecisionEnvironment, LongHorizonEpisodeRunner, ScenarioGenerator, EraDecisionAgent
from modules.decision_pipeline import DecisionPipelineEngine


def test_long_horizon_environment_steps() -> None:
    env = LongHorizonDecisionEnvironment(generator=ScenarioGenerator(seed=5), max_steps=3)
    state = env.reset()
    assert state.step_index == 0
    next_state, reward, done, _info = env.step("launch_feature")
    assert next_state.step_index == 1
    assert isinstance(reward, float)


def test_long_horizon_episode_runner_runs() -> None:
    pipeline = DecisionPipelineEngine.create()
    agent = EraDecisionAgent(pipeline=pipeline, requested_mode="meeting")
    env = LongHorizonDecisionEnvironment(generator=ScenarioGenerator(seed=3), max_steps=2)
    runner = LongHorizonEpisodeRunner(environment=env, agent=agent)
    episode = runner.run_episode(episode_index=1)
    assert episode.steps
