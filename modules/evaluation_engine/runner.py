"""Evaluation runner for ERA-Bench scenarios."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.decision_pipeline import DecisionPipelineEngine
from modules.decision_simulator import DecisionSimulator
from modules.value_model import ValueModelPredictor
from modules.policy_model import PolicyModelPredictor
from modules.learning_core import augment_context_with_knowledge

from .calibration import expected_calibration_error
from .llm_baseline import run_llm_baseline
from .metrics import accuracy_score, average, clamp_score
from .option_match import match_option
from .regret import regret_score
from .rubric_eval import rubric_score


@dataclass
class OptionEvaluation:
    option: str
    score: float
    confidence: float
    decision: str
    reasoning: str
    utility: float
    prediction: Dict[str, Any]


class EvaluationRunner:
    def __init__(
        self,
        scenarios: List[Dict[str, Any]],
        *,
        requested_mode: Optional[str] = None,
        baseline_provider: str = "none",
        baseline_model: Optional[str] = None,
        baseline_temperature: float = 0.0,
        enable_counterfactuals: bool = False,
        decision_policy: str = "hybrid",
        value_model_path: Optional[str] = None,
        value_weight: float = 0.4,
        policy_model_path: Optional[str] = None,
        policy_weight: float = 0.6,
        policy_top_k: Optional[int] = None,
    ) -> None:
        self.scenarios = scenarios
        self.pipeline = DecisionPipelineEngine.create()
        self.simulator = DecisionSimulator()
        self.value_model = ValueModelPredictor(Path(value_model_path)) if value_model_path else None
        self.value_weight = float(value_weight)
        self.policy_model = PolicyModelPredictor(Path(policy_model_path)) if policy_model_path else None
        self.policy_weight = float(policy_weight)
        self.policy_top_k = int(policy_top_k) if policy_top_k is not None else None
        self.requested_mode = requested_mode
        self.baseline_provider = baseline_provider
        self.baseline_model = baseline_model
        self.baseline_temperature = baseline_temperature
        self.enable_counterfactuals = enable_counterfactuals
        self.decision_policy = str(decision_policy or "era").strip().lower()
        if (
            self.decision_policy == "hybrid"
            and self.policy_model is not None
            and self.value_model is not None
        ):
            self.decision_policy = "hybrid_all"

    def run(self) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for scenario in self.scenarios:
            era = self.run_era(scenario)
            baseline = run_llm_baseline(
                scenario,
                provider=self.baseline_provider,
                model=self.baseline_model,
                temperature=self.baseline_temperature,
            )
            results.append(
                {
                    "scenario_id": scenario.get("scenario_id"),
                    "category": scenario.get("category"),
                    "difficulty": scenario.get("difficulty"),
                    "expected_decision": scenario.get("expected_decision", ""),
                    "era": era,
                    "baseline": baseline,
                }
            )

        return self.aggregate(results)

    def run_era(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        options = scenario.get("decision_options") or []
        option_evals: List[OptionEvaluation] = []
        counterfactuals: Dict[str, str] = {}
        enriched_context = augment_context_with_knowledge(
            scenario.get("context", {}),
            scenario.get("prompt", ""),
        )
        simulator_utilities = self.simulator.compute_utilities(scenario)
        simulator_best = max(simulator_utilities, key=lambda item: item.utility) if simulator_utilities else None
        prediction_map = {item.option: item.prediction for item in simulator_utilities}
        utility_map = {item.option: item.utility for item in simulator_utilities}
        value_scores: Dict[str, float] = {}
        policy_scores: Dict[str, float] = {}

        candidate_options = options
        if self.policy_model is not None and self.policy_top_k:
            for option in options:
                policy_scores[str(option)] = self.policy_model.predict(
                    scenario.get("prompt", ""),
                    str(option),
                    scenario.get("context", {}),
                )
            ranked = sorted(
                options,
                key=lambda opt: policy_scores.get(str(opt), 0.0),
                reverse=True,
            )
            candidate_options = ranked[: self.policy_top_k]

        for option in candidate_options:
            result = self.pipeline.run(
                user_input=self._build_option_prompt(scenario, option),
                requested_mode=self.requested_mode or scenario.get("mode") or "meeting",
                metadata={
                    "scenario_id": scenario.get("scenario_id"),
                    "benchmark": "era_bench",
                    "candidate_option": option,
                },
                source="era_benchmark",
            )
            decision = str(result.decision_contract.decision or "").strip().lower()
            confidence = float(result.decision_contract.confidence or 0.0)
            reasoning = self._extract_reasoning(result)
            score = self._score_option(result, confidence)
            if self.value_model is not None:
                value_scores[str(option)] = self.value_model.predict(
                    scenario.get("prompt", ""),
                    str(option),
                    enriched_context,
                )
            if self.policy_model is not None and str(option) not in policy_scores:
                policy_scores[str(option)] = self.policy_model.predict(
                    scenario.get("prompt", ""),
                    str(option),
                    enriched_context,
                )
            prediction = prediction_map.get(str(option))
            option_evals.append(
                OptionEvaluation(
                    option=str(option),
                    score=score,
                    confidence=confidence,
                    decision=decision,
                    reasoning=reasoning,
                    utility=utility_map.get(str(option), 0.0),
                    prediction=prediction.__dict__ if prediction else {},
                )
            )
            if self.enable_counterfactuals:
                counterfactuals[str(option)] = self._run_counterfactual(scenario, option)

        option_evals.sort(key=lambda item: (item.score, item.confidence, item.option), reverse=True)
        default_choice = option_evals[0] if option_evals else OptionEvaluation("", 0.0, 0.0, "", "", 0.0, {})
        chosen = default_choice

        option_scores = {item.option: item.score for item in option_evals}
        option_utilities = {item.option: item.utility for item in simulator_utilities}
        expected = scenario.get("expected_decision", "")
        combined_scores: Dict[str, float] = {}
        policy_value_scores: Dict[str, float] = {}
        hybrid_all_scores: Dict[str, float] = {}
        if self.value_model is not None:
            for item in option_evals:
                value_score = value_scores.get(item.option, 0.0)
                combined_scores[item.option] = round(
                    (1 - self.value_weight) * item.score + self.value_weight * value_score,
                    4,
                )
        if self.policy_model is not None and self.value_model is not None:
            for item in option_evals:
                policy_score = policy_scores.get(item.option, 0.0)
                value_score = value_scores.get(item.option, 0.0)
                policy_value_scores[item.option] = round(
                    self.policy_weight * policy_score + (1 - self.policy_weight) * value_score,
                    4,
                )
        if self.policy_model is not None and self.value_model is not None:
            for item in option_evals:
                policy_score = policy_scores.get(item.option, 0.0)
                value_score = value_scores.get(item.option, 0.0)
                reasoning_score = clamp_score(item.score)
                hybrid_all_scores[item.option] = round(
                    0.5 * value_score + 0.3 * reasoning_score + 0.2 * policy_score,
                    4,
                )

        if self.decision_policy == "simulator" and simulator_best:
            chosen = next(
                (item for item in option_evals if item.option == simulator_best.option),
                default_choice,
            )
        elif self.decision_policy == "hybrid" and option_evals and simulator_best:
            def _normalize(value: float) -> float:
                return max(0.0, min(1.0, (value + 1.0) / 2.0))
            sim_score = _normalize(simulator_best.utility)
            best = None
            for item in option_evals:
                base_score = combined_scores.get(item.option, item.score)
                era_score = _normalize(base_score)
                combined = 0.7 * era_score + 0.3 * sim_score if item.option == simulator_best.option else 0.7 * era_score
                key = (combined, item.confidence, item.option)
                if best is None or key > best[0]:
                    best = (key, item)
            if best:
                chosen = best[1]
        elif self.decision_policy in ("value_model", "hybrid_value") and combined_scores:
            best_option = max(combined_scores.items(), key=lambda kv: kv[1])[0]
            chosen = next((item for item in option_evals if item.option == best_option), chosen)
        elif self.decision_policy == "policy_model" and policy_scores:
            best_option = max(policy_scores.items(), key=lambda kv: kv[1])[0]
            chosen = next((item for item in option_evals if item.option == best_option), chosen)
        elif self.decision_policy == "hybrid_policy_value" and policy_value_scores:
            best_option = max(policy_value_scores.items(), key=lambda kv: kv[1])[0]
            chosen = next((item for item in option_evals if item.option == best_option), chosen)
        elif self.decision_policy == "hybrid_all" and hybrid_all_scores:
            best_option = max(hybrid_all_scores.items(), key=lambda kv: kv[1])[0]
            chosen = next((item for item in option_evals if item.option == best_option), chosen)

        normalized_chosen = match_option(chosen.option, options) or chosen.option
        decision_correct = accuracy_score(normalized_chosen, expected)
        rubric = scenario.get("reasoning_rubric", [])
        reasoning_text = chosen.reasoning
        if normalized_chosen in prediction_map:
            hints = self.simulator.reasoning_hints(scenario, prediction_map[normalized_chosen])
            if hints:
                reasoning_text = f"{reasoning_text} {' '.join(hints)}".strip()
        if self.enable_counterfactuals and normalized_chosen in counterfactuals:
            reasoning_text = f"{reasoning_text} {counterfactuals[normalized_chosen]}".strip()
        rubric_hit_score = rubric_score(reasoning_text, rubric)

        evaluation_weights = scenario.get("evaluation", {})
        w_decision = float(evaluation_weights.get("decision_weight", 0.5))
        w_reason = float(evaluation_weights.get("reasoning_weight", 0.5))
        total_w = w_decision + w_reason
        if not math.isclose(total_w, 1.0) and total_w > 0:
            w_decision /= total_w
            w_reason /= total_w

        combined_score = w_decision * decision_correct + w_reason * rubric_hit_score

        return {
            "decision": normalized_chosen,
            "confidence": clamp_score(chosen.confidence),
            "reasoning": reasoning_text,
            "score": round(combined_score, 4),
            "value": option_utilities.get(normalized_chosen, 0.0),
            "decision_correct": decision_correct,
            "rubric_score": rubric_hit_score,
            "regret": regret_score(option_utilities, chosen.option),
            "option_scores": option_scores,
            "option_utilities": option_utilities,
            "option_values": option_utilities,
            "option_value_scores": value_scores,
            "option_combined_scores": combined_scores,
            "option_policy_scores": policy_scores,
            "option_policy_value_scores": policy_value_scores,
            "option_hybrid_all_scores": hybrid_all_scores,
            "option_evaluations": [item.__dict__ for item in option_evals],
            "simulator_choice": simulator_best.option if simulator_best else "",
            "simulator_utility": simulator_best.utility if simulator_best else 0.0,
            "counterfactuals": counterfactuals if self.enable_counterfactuals else {},
            "decision_policy": self.decision_policy,
        }

    @staticmethod
    def _build_option_prompt(scenario: Dict[str, Any], option: str) -> str:
        raw_options = scenario.get("decision_options", [])
        labeled = []
        for idx, item in enumerate(raw_options):
            label = chr(ord("A") + idx)
            labeled.append(f"{label}. {item}")
        options = "\n".join(labeled)
        return "\n".join(
            [
                "Scenario:",
                scenario.get("prompt", ""),
                "",
                "Options:",
                options,
                "",
                "Evaluate the following option:",
                f"Option: {option}",
                "Explain pros and cons.",
                "Return score from 0-1.",
            ]
        )

    @staticmethod
    def _extract_reasoning(result: Any) -> str:
        final_decision = getattr(result, "final_decision", {}) or {}
        rationale = ""
        if isinstance(final_decision, Mapping):
            rationale = str(final_decision.get("reason", "")).strip()
        if not rationale and getattr(result, "decision_contract", None):
            rationale = str(result.decision_contract.rationale or "").strip()
        knowledge_result = getattr(result, "knowledge_result", {}) or getattr(result, "knowledge_contract", {}) or {}
        synthesized = knowledge_result.get("synthesized_items") or knowledge_result.get("synthesized_knowledge") or []
        if isinstance(synthesized, Iterable) and not isinstance(synthesized, (str, bytes, bytearray)):
            rationale = f"{rationale} {' '.join(map(str, synthesized))}".strip()
        return rationale.lower()

    @staticmethod
    def _score_option(result: Any, confidence: float) -> float:
        decision = str(result.decision_contract.decision or "").strip().lower()
        recommendation = str(result.decision_packaging_contract.recommendation or "").strip().lower()
        red_line_count = int(result.decision_packaging_contract.red_line_count or 0)
        requires_followup = bool(result.decision_packaging_contract.requires_followup)

        base_scores = {
            "accept": 1.0,
            "accept_with_mitigation": 0.65,
            "direct_response": 0.35,
            "defer": 0.0,
            "reject": -1.0,
        }
        score = base_scores.get(decision, 0.0)
        score += max(0.0, min(1.0, confidence))
        if recommendation == "support":
            score += 0.15
        elif recommendation == "oppose":
            score -= 0.15
        score -= red_line_count * 0.2
        if requires_followup:
            score -= 0.1
        return round(score, 4)

    def _run_counterfactual(self, scenario: Dict[str, Any], option: str) -> str:
        prompt = "\n".join(
            [
                "Counterfactual simulation:",
                scenario.get("prompt", ""),
                "",
                f"If we choose option: {option}",
                "What likely happens next? Be specific and concise.",
            ]
        )
        result = self.pipeline.run(
            user_input=prompt,
            requested_mode=self.requested_mode or scenario.get("mode") or "meeting",
            metadata={
                "scenario_id": scenario.get("scenario_id"),
                "benchmark": "era_bench",
                "counterfactual": option,
            },
            source="era_benchmark",
        )
        return self._extract_reasoning(result)

    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        era_predictions = [
            {
                "confidence": item["era"]["confidence"],
                "correct": bool(item["era"]["decision_correct"]),
            }
            for item in results
        ]
        era_accuracy = average(item["era"]["decision_correct"] for item in results)
        era_regret = average(item["era"]["regret"] for item in results)
        era_rubric = average(item["era"]["rubric_score"] for item in results)
        era_ece = expected_calibration_error(era_predictions)

        categories: Dict[str, List[float]] = {}
        for item in results:
            categories.setdefault(item["category"], []).append(item["era"]["score"])

        simulator_accuracy = average(
            accuracy_score(item["era"].get("simulator_choice", ""), item.get("expected_decision", ""))
            for item in results
        )

        baseline = {}
        if results and results[0]["baseline"].get("status") == "ok":
            baseline_accuracy = average(
                accuracy_score(item["baseline"]["decision"], item.get("expected_decision", ""))
                for item in results
            )
            baseline_regret = average(item["era"]["regret"] for item in results)
            baseline_rubric = average(
                rubric_score(item["baseline"].get("reasoning", ""), []) for item in results
            )
            baseline = {
                "accuracy": baseline_accuracy,
                "avg_regret": baseline_regret,
                "rubric_score": baseline_rubric,
                "ece": 0.0,
            }

        return {
            "scenario_count": len(results),
            "era": {
                "accuracy": round(era_accuracy, 4),
                "avg_regret": round(era_regret, 4),
                "rubric_score": round(era_rubric, 4),
                "ece": era_ece,
            },
            "simulator": {
                "accuracy": round(simulator_accuracy, 4),
            },
            "baseline": baseline,
            "category_scores": {
                cat: round(average(values), 4) for cat, values in sorted(categories.items())
            },
            "results": results,
        }


def load_scenarios(
    root: Path,
    *,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    scenario_ids: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    allowed_ids = {str(item) for item in scenario_ids} if scenario_ids else None
    categories = [category] if category else [p.name for p in (root / "scenarios").iterdir() if p.is_dir()]
    for cat in sorted(categories):
        for path in sorted((root / "scenarios" / cat).glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if allowed_ids is not None and data.get("scenario_id") not in allowed_ids:
                continue
            scenarios.append(data)
            if limit and len(scenarios) >= limit:
                return scenarios
    return scenarios
