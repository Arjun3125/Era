"""Episode execution that embeds ERA as the acting policy."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.decision_pipeline import DecisionPipelineEngine

from .environment import DecisionEnvironment
from .reward_function import RewardBreakdown
from .scenario_generator import DecisionScenario, ScenarioOption
from .simulator import SimulationOutcome


@dataclass
class PolicyEvaluation:
    """Policy judgment for one candidate option evaluated through ERA."""

    scenario_id: str
    action_label: str
    action_title: str
    score: float
    predicted_utility: float
    pipeline_decision: str
    recommendation: str
    confidence: float
    rationale: str
    red_line_count: int
    requires_followup: bool
    mode: str
    run_id: str
    selected_ministers: List[str] = field(default_factory=list)
    final_decision: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "action_label": self.action_label,
            "action_title": self.action_title,
            "score": self.score,
            "predicted_utility": self.predicted_utility,
            "pipeline_decision": self.pipeline_decision,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "red_line_count": self.red_line_count,
            "requires_followup": self.requires_followup,
            "mode": self.mode,
            "run_id": self.run_id,
            "selected_ministers": list(self.selected_ministers),
            "final_decision": dict(self.final_decision),
        }


@dataclass
class EpisodeRecord:
    """Full one-episode record suitable for later learning or benchmarking."""

    episode_index: int
    scenario: DecisionScenario
    chosen_action: PolicyEvaluation
    policy_evaluations: List[PolicyEvaluation]
    outcome: SimulationOutcome
    reward: float
    reward_breakdown: RewardBreakdown
    done: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "episode_index": self.episode_index,
            "scenario": self.scenario.as_dict(),
            "chosen_action": self.chosen_action.as_dict(),
            "policy_evaluations": [item.as_dict() for item in self.policy_evaluations],
            "outcome": self.outcome.as_dict(),
            "reward": self.reward,
            "reward_breakdown": self.reward_breakdown.as_dict(),
            "done": self.done,
        }


@dataclass
class TrainingLoopSummary:
    """Aggregate report over a batch of one-step environment episodes."""

    episode_count: int
    average_reward: float
    best_reward: float
    worst_reward: float
    decision_counts: Dict[str, int]
    action_counts: Dict[str, int]
    domain_counts: Dict[str, int]
    episodes: List[EpisodeRecord] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "episode_count": self.episode_count,
            "average_reward": self.average_reward,
            "best_reward": self.best_reward,
            "worst_reward": self.worst_reward,
            "decision_counts": dict(self.decision_counts),
            "action_counts": dict(self.action_counts),
            "domain_counts": dict(self.domain_counts),
            "episodes": [episode.as_dict() for episode in self.episodes],
        }


class EraDecisionAgent:
    """Evaluates each scenario option through ERA and chooses the highest-scoring action."""

    _DECISION_BASE_SCORES = {
        "accept": 1.0,
        "accept_with_mitigation": 0.65,
        "direct_response": 0.35,
        "defer": 0.0,
        "reject": -1.0,
    }

    def __init__(
        self,
        *,
        pipeline: DecisionPipelineEngine,
        requested_mode: str | None = "meeting",
    ):
        self.pipeline = pipeline
        self.requested_mode = str(requested_mode or "meeting").strip() or "meeting"

    def choose_action(
        self,
        scenario: DecisionScenario,
    ) -> tuple[PolicyEvaluation, List[PolicyEvaluation]]:
        evaluations = [
            self.evaluate_option(scenario, option)
            for option in scenario.options
        ]
        ranked = sorted(
            evaluations,
            key=lambda item: (item.score, item.confidence, item.action_label),
            reverse=True,
        )
        return ranked[0], ranked

    def evaluate_option(
        self,
        scenario: DecisionScenario,
        option: ScenarioOption,
    ) -> PolicyEvaluation:
        result = self.pipeline.run(
            user_input=self._build_option_prompt(scenario, option),
            requested_mode=self.requested_mode or scenario.requested_mode,
            metadata={
                "scenario_id": scenario.scenario_id,
                "scenario_domain": scenario.domain,
                "candidate_option": option.label,
                "candidate_title": option.title,
                "source": "decision_env",
            },
            source="decision_env",
        )
        decision = str(result.decision_contract.decision).strip().lower() or "defer"
        recommendation = (
            str(result.decision_packaging_contract.recommendation).strip().lower() or "defer"
        )
        confidence = float(result.decision_contract.confidence or 0.0)
        red_line_count = int(result.decision_packaging_contract.red_line_count or 0)
        requires_followup = bool(result.decision_packaging_contract.requires_followup)
        predicted_utility = self._estimate_option_utility(scenario, option)
        score = self._score_policy_evaluation(
            decision=decision,
            confidence=confidence,
            recommendation=recommendation,
            red_line_count=red_line_count,
            requires_followup=requires_followup,
            predicted_utility=predicted_utility,
        )
        return PolicyEvaluation(
            scenario_id=scenario.scenario_id,
            action_label=option.label,
            action_title=option.title,
            score=score,
            predicted_utility=predicted_utility,
            pipeline_decision=decision,
            recommendation=recommendation,
            confidence=confidence,
            rationale=str(result.decision_contract.rationale or ""),
            red_line_count=red_line_count,
            requires_followup=requires_followup,
            mode=str(result.mode_resolution.mode or self.requested_mode),
            run_id=str(result.run_id),
            selected_ministers=list(result.mode_resolution.selected_ministers or []),
            final_decision=dict(result.final_decision or {}),
        )

    def _score_policy_evaluation(
        self,
        *,
        decision: str,
        confidence: float,
        recommendation: str,
        red_line_count: int,
        requires_followup: bool,
        predicted_utility: float,
    ) -> float:
        score = self._DECISION_BASE_SCORES.get(decision, 0.0)
        score += max(0.0, min(1.0, confidence))
        if recommendation == "support":
            score += 0.15
        elif recommendation == "oppose":
            score -= 0.15
        score -= red_line_count * 0.2
        if requires_followup:
            score -= 0.1
        score += max(-1.0, min(1.0, predicted_utility / 20.0))
        return round(score, 4)

    @staticmethod
    def _estimate_option_utility(
        scenario: DecisionScenario,
        option: ScenarioOption,
    ) -> float:
        metrics = scenario.simulated_outcomes.get(option.label, {})
        total = 0.0
        for metric_name, raw_value in metrics.items():
            weight = float(scenario.reward_weights.get(metric_name, 0.0))
            total += weight * float(raw_value)
        return round(total, 4)

    @staticmethod
    def _build_option_prompt(
        scenario: DecisionScenario,
        option: ScenarioOption,
    ) -> str:
        return "\n".join(
            [
                "You are evaluating one candidate action inside a discrete decision environment.",
                scenario.to_prompt(),
                "",
                f"Candidate option under review: {option.label} - {option.title}",
                f"Candidate details: {option.description}",
                "",
                "Judge whether this candidate should be accepted, accepted with mitigation, deferred, or rejected.",
                "Prefer survivability, downside control, and strategic robustness over shallow optimism.",
            ]
        )


class EpisodeRunner:
    """Runs single episodes or training-style loops over the embedded environment."""

    def __init__(
        self,
        *,
        environment: DecisionEnvironment,
        agent: EraDecisionAgent,
    ):
        self.environment = environment
        self.agent = agent

    def run_episode(
        self,
        *,
        episode_index: int,
        domain: Optional[str] = None,
    ) -> EpisodeRecord:
        scenario = self.environment.reset(domain=domain)
        chosen_action, evaluations = self.agent.choose_action(scenario)
        outcome, reward, done = self.environment.step(chosen_action.action_label)
        reward_breakdown = self.environment.last_reward_breakdown or RewardBreakdown(total=reward)
        return EpisodeRecord(
            episode_index=episode_index,
            scenario=scenario,
            chosen_action=chosen_action,
            policy_evaluations=evaluations,
            outcome=outcome,
            reward=reward,
            reward_breakdown=reward_breakdown,
            done=done,
        )

    def run_training_loop(
        self,
        *,
        episode_count: int,
        domain: Optional[str] = None,
        experience_log_path: str | None = None,
    ) -> TrainingLoopSummary:
        if episode_count <= 0:
            raise ValueError("episode_count must be positive.")

        episodes: List[EpisodeRecord] = []
        decision_counts: Dict[str, int] = {}
        action_counts: Dict[str, int] = {}
        domain_counts: Dict[str, int] = {}
        total_reward = 0.0
        best_reward = float("-inf")
        worst_reward = float("inf")

        for episode_index in range(1, episode_count + 1):
            episode = self.run_episode(episode_index=episode_index, domain=domain)
            episodes.append(episode)
            total_reward += episode.reward
            best_reward = max(best_reward, episode.reward)
            worst_reward = min(worst_reward, episode.reward)

            decision_key = episode.chosen_action.pipeline_decision
            decision_counts[decision_key] = decision_counts.get(decision_key, 0) + 1

            action_key = episode.chosen_action.action_label
            action_counts[action_key] = action_counts.get(action_key, 0) + 1

            domain_key = episode.scenario.domain
            domain_counts[domain_key] = domain_counts.get(domain_key, 0) + 1

        summary = TrainingLoopSummary(
            episode_count=episode_count,
            average_reward=round(total_reward / episode_count, 4),
            best_reward=round(best_reward, 4),
            worst_reward=round(worst_reward, 4),
            decision_counts=decision_counts,
            action_counts=action_counts,
            domain_counts=domain_counts,
            episodes=episodes,
        )
        if experience_log_path:
            self._write_experience_log(summary, experience_log_path)
        return summary

    @staticmethod
    def _write_experience_log(
        summary: TrainingLoopSummary,
        experience_log_path: str,
    ) -> None:
        path = Path(experience_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for episode in summary.episodes:
                handle.write(json.dumps(episode.as_dict(), ensure_ascii=True))
                handle.write("\n")
