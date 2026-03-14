from __future__ import annotations

from decision_env import MultiStepDecisionEnvironment, MultiStepEpisodeRunner, ScenarioGenerator, EraDecisionAgent
from modules.decision_pipeline import DecisionPipelineEngine


def test_multistep_environment_progresses() -> None:
    env = MultiStepDecisionEnvironment(generator=ScenarioGenerator(seed=7), max_steps=2)
    state = env.reset()
    assert state.step_index == 0
    next_state, reward, done, info = env.step("A")
    assert next_state.step_index == 1
    assert isinstance(reward, float)
    assert "transition" in info
    if not done:
        next_state, reward, done, info = env.step("A")
        assert done


def test_multistep_episode_runner_runs() -> None:
    pipeline = DecisionPipelineEngine.create()
    agent = EraDecisionAgent(pipeline=pipeline, requested_mode="meeting")
    env = MultiStepDecisionEnvironment(generator=ScenarioGenerator(seed=9), max_steps=2)
    runner = MultiStepEpisodeRunner(environment=env, agent=agent)
    summary = runner.run_training_loop(episode_count=1)
    assert summary.episode_count == 1
    assert summary.episodes
