from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_env import DecisionEnvironment, EpisodeRunner, EraDecisionAgent, ScenarioGenerator
from modules.decision_pipeline import DecisionPipelineEngine


class FakePipeline:
    def __init__(self):
        self._responses = {
            "A": self._result("run-a", "accept", "support", 0.8, 0, False),
            "B": self._result("run-b", "reject", "oppose", 0.9, 0, False),
            "C": self._result("run-c", "accept_with_mitigation", "support", 0.7, 1, True),
        }

    def run(self, *, user_input, requested_mode=None, metadata=None, source=None):
        label = "A"
        marker = "Candidate option under review: "
        if marker in user_input:
            label = user_input.split(marker, 1)[1].split(" - ", 1)[0].strip().upper()
        return self._responses[label]

    @staticmethod
    def _result(run_id, decision, recommendation, confidence, red_line_count, requires_followup):
        return SimpleNamespace(
            run_id=run_id,
            decision_contract=SimpleNamespace(
                decision=decision,
                confidence=confidence,
                rationale=f"rationale-{run_id}",
            ),
            decision_packaging_contract=SimpleNamespace(
                recommendation=recommendation,
                red_line_count=red_line_count,
                requires_followup=requires_followup,
            ),
            mode_resolution=SimpleNamespace(
                mode="meeting",
                selected_ministers=["risk", "strategy"],
            ),
            final_decision={
                "final_outcome": decision,
                "confidence": confidence,
                "reason": f"reason-{run_id}",
            },
        )


def test_scenario_generator_returns_requested_domain():
    generator = ScenarioGenerator(seed=7)

    scenario = generator.generate(domain="startup")

    assert scenario.domain == "startup"
    assert len(scenario.options) == 3
    assert {option.label for option in scenario.options} == {"A", "B", "C"}


def test_environment_reset_and_step_produce_reward():
    environment = DecisionEnvironment(generator=ScenarioGenerator(seed=3), default_domain="startup")

    scenario = environment.reset()
    outcome, reward, done = environment.step("B")

    assert scenario.domain == "startup"
    assert outcome.action_label == "B"
    assert done is True
    assert reward == environment.last_reward_breakdown.total
    assert "risk" in environment.last_reward_breakdown.weighted_metrics


def test_episode_runner_uses_pipeline_scores_and_writes_experience_log(tmp_path):
    environment = DecisionEnvironment(generator=ScenarioGenerator(seed=11), default_domain="startup")
    agent = EraDecisionAgent(pipeline=FakePipeline(), requested_mode="meeting")
    runner = EpisodeRunner(environment=environment, agent=agent)
    log_path = tmp_path / "episodes.jsonl"

    summary = runner.run_training_loop(
        episode_count=2,
        domain="startup",
        experience_log_path=str(log_path),
    )

    assert summary.episode_count == 2
    assert summary.action_counts["A"] == 2
    assert summary.decision_counts["accept"] == 2
    assert log_path.exists()
    assert len(log_path.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_real_pipeline_can_act_as_agent_smoke():
    scenario = ScenarioGenerator(seed=19).generate(domain="risk_management")
    agent = EraDecisionAgent(
        pipeline=DecisionPipelineEngine.create(),
        requested_mode="meeting",
    )

    chosen_action, evaluations = agent.choose_action(scenario)

    assert chosen_action.action_label in {"A", "B", "C"}
    assert len(evaluations) == len(scenario.options)
    assert all(item.run_id for item in evaluations)


def test_environment_step_requires_reset():
    environment = DecisionEnvironment()

    with pytest.raises(RuntimeError):
        environment.step("A")
