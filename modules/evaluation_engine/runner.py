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

from .calibration import brier_score, expected_calibration_error
from modules.uncertainty import RiskModel
from modules.calibration import ProbabilityCalibrator
from .llm_baseline import run_llm_baseline
from .metrics import accuracy_score, average, clamp_score
from .budget_metrics import ComputeCostConfig, aggregate_budget_metrics
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
    council_signal: float
    council_metrics: Dict[str, Any]


class EvaluationRunner:
    def __init__(
        self,
        scenarios: List[Dict[str, Any]],
        *,
        requested_mode: Optional[str] = None,
        routing_context: Optional[Mapping[str, Any]] = None,
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
        self.routing_context = dict(routing_context) if isinstance(routing_context, Mapping) else None
        self._calibration_cache: Dict[tuple[str, str], Optional[ProbabilityCalibrator]] = {}
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
        if self.value_model is not None:
            self.value_model.warm_cache(
                scenario.get("prompt", ""),
                options,
                enriched_context,
            )
        if self.policy_model is not None:
            self.policy_model.warm_cache(
                scenario.get("prompt", ""),
                options,
                enriched_context,
            )
        simulator_utilities = self.simulator.compute_utilities(scenario)
        simulator_best = max(simulator_utilities, key=lambda item: item.utility) if simulator_utilities else None
        prediction_map = {item.option: item.prediction for item in simulator_utilities}
        utility_map = {item.option: item.utility for item in simulator_utilities}
        value_scores: Dict[str, float] = {}
        policy_scores: Dict[str, float] = {}
        merged_routing = dict(self.routing_context or {})

        if self.policy_model is not None:
            for option in options:
                policy_scores[str(option)] = self.policy_model.predict(
                    scenario.get("prompt", ""),
                    str(option),
                    enriched_context,
                )
        if self.value_model is not None:
            for option in options:
                value_scores[str(option)] = self.value_model.predict(
                    scenario.get("prompt", ""),
                    str(option),
                    enriched_context,
                )

        if policy_scores:
            merged_routing["policy_entropy"] = self._policy_entropy(policy_scores)
        if value_scores:
            merged_routing["value_variance"] = self._value_variance(value_scores)
        merged_routing["risk_score"] = RiskModel().score(
            policy_entropy=merged_routing.get("policy_entropy"),
            value_variance=merged_routing.get("value_variance"),
            dissent_level=merged_routing.get("dissent_level"),
        )

        probe_metrics: Dict[str, float] = {}
        if merged_routing.get("probe_minister"):
            self._run_probe_minister(scenario, merged_routing)
            probe_metrics = {
                "probe_support_ratio": float(merged_routing.get("probe_support_ratio", 0.0)),
                "probe_consensus_strength": float(merged_routing.get("probe_consensus_strength", 0.0)),
                "probe_confidence_mean": float(merged_routing.get("probe_confidence_mean", 0.0)),
                "minister_disagreement": float(merged_routing.get("minister_disagreement", 0.0)),
            }

        candidate_options = options
        if self.policy_model is not None and self.policy_top_k:
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
                routing_context=merged_routing,
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
            council_metrics = self._extract_council_metrics(result)
            council_signal = council_metrics["council_signal"]
            calibrated_confidence = self._calibrate_confidence(
                confidence,
                routing_context=merged_routing,
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
                    council_signal=council_signal,
                    council_metrics=council_metrics,
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
            weights = self._resolve_hybrid_weights(self.routing_context)
            for item in option_evals:
                policy_score = policy_scores.get(item.option, 0.0)
                value_score = value_scores.get(item.option, 0.0)
                council_signal = item.council_signal
                hybrid_all_scores[item.option] = round(
                    weights["value"] * value_score
                    + weights["policy"] * policy_score
                    + weights["council"] * council_signal,
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
        reasoning_budget = self._extract_reasoning_budget(result)
        calibrated_confidence = self._calibrate_confidence(
            chosen.confidence,
            routing_context=merged_routing,
        )
        risk_score = RiskModel().score(
            policy_entropy=merged_routing.get("policy_entropy"),
            value_variance=merged_routing.get("value_variance"),
            dissent_level=chosen.council_metrics.get("dissent_level"),
        )

        return {
            "decision": normalized_chosen,
            "confidence": clamp_score(chosen.confidence),
            "confidence_calibrated": clamp_score(calibrated_confidence),
            "policy_entropy": merged_routing.get("policy_entropy", 0.0),
            "value_variance": merged_routing.get("value_variance", 0.0),
            "risk_score": risk_score,
            "reasoning": reasoning_text,
            "score": round(combined_score, 4),
            "reasoning_budget": reasoning_budget,
            "minister_count": int(chosen.council_metrics.get("minister_count", 0)),
            "probe_metrics": probe_metrics,
            "value": option_utilities.get(normalized_chosen, 0.0),
            "decision_correct": decision_correct,
            "rubric_score": rubric_hit_score,
            "regret": regret_score(option_utilities, chosen.option),
            "council_metrics": chosen.council_metrics,
            "option_scores": option_scores,
            "option_utilities": option_utilities,
            "option_values": option_utilities,
            "option_value_scores": value_scores,
            "option_combined_scores": combined_scores,
            "option_policy_scores": policy_scores,
            "option_policy_value_scores": policy_value_scores,
            "option_hybrid_all_scores": hybrid_all_scores,
            "option_council_signals": {item.option: item.council_signal for item in option_evals},
            "option_evaluations": [item.__dict__ for item in option_evals],
            "simulator_choice": simulator_best.option if simulator_best else "",
            "simulator_utility": simulator_best.utility if simulator_best else 0.0,
            "counterfactuals": counterfactuals if self.enable_counterfactuals else {},
            "decision_policy": self.decision_policy,
            "hybrid_weights": self._resolve_hybrid_weights(self.routing_context),
        }

    @staticmethod
    def _resolve_hybrid_weights(routing_context: Optional[Mapping[str, Any]]) -> Dict[str, float]:
        default = {"value": 0.45, "policy": 0.25, "council": 0.30}
        return default

    @staticmethod
    def _policy_entropy(scores: Dict[str, float]) -> float:
        if not scores:
            return 0.0
        values = [max(0.0, float(value)) for value in scores.values()]
        total = sum(values)
        if total <= 0:
            return 0.0
        probs = [value / total for value in values if value > 0]
        if not probs:
            return 0.0
        entropy = -sum(p * math.log(p + 1e-12) for p in probs)
        max_entropy = math.log(len(probs)) if len(probs) > 1 else 1.0
        return round(entropy / max_entropy if max_entropy > 0 else 0.0, 4)

    @staticmethod
    def _value_variance(scores: Dict[str, float]) -> float:
        if not scores:
            return 0.0
        values = [float(value) for value in scores.values()]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return round(variance, 4)

    def _run_probe_minister(
        self,
        scenario: Dict[str, Any],
        routing_context: Dict[str, Any],
    ) -> None:
        options = scenario.get("decision_options") or []
        if not options:
            return
        probe_minister = str(routing_context.get("probe_minister") or "risk").strip().lower()
        probe_label = str(routing_context.get("probe_label") or "").strip()
        probe_option = next((opt for opt in options if str(opt) == probe_label), options[0])
        probe_context = dict(routing_context)
        probe_context.update(
            {
                "force_ministers": [probe_minister],
                "expert_router_enabled": False,
                "disable_ministers": False,
                "requested_mode": "meeting",
                "probe_pass": True,
            }
        )
        result = self.pipeline.run(
            user_input=self._build_option_prompt(scenario, probe_option),
            requested_mode=self.requested_mode or scenario.get("mode") or "meeting",
            routing_context=probe_context,
            metadata={
                "scenario_id": scenario.get("scenario_id"),
                "probe_minister": probe_minister,
                "probe_option": probe_option,
            },
            source="era_benchmark_probe",
        )
        metrics = self._extract_council_metrics(result)
        routing_context["probe_support_ratio"] = metrics.get("support_ratio", 0.0)
        routing_context["probe_consensus_strength"] = metrics.get("consensus_strength", 0.0)
        routing_context["probe_confidence_mean"] = metrics.get("confidence_mean", 0.0)
        routing_context["minister_disagreement"] = round(
            1.0 - float(metrics.get("consensus_strength", 0.0)),
            4,
        )

    @staticmethod
    def _extract_council_metrics(result: Any) -> Dict[str, Any]:
        council = getattr(result, "council_result", {}) or {}
        minister_positions = council.get("minister_positions") or council.get("minister_outputs") or {}
        if not isinstance(minister_positions, Mapping):
            minister_positions = {}
        support_count = int(council.get("support_count") or 0)
        oppose_count = int(council.get("oppose_count") or 0)
        neutral_count = int(council.get("neutral_count") or 0)
        total = int(council.get("total_ministers_consulted") or 0)
        if total <= 0 and minister_positions:
            total = len(minister_positions)
        if total <= 0:
            support_count = oppose_count = neutral_count = 0
        if total > 0 and (support_count + oppose_count + neutral_count) == 0:
            support_count = sum(
                1 for item in minister_positions.values() if str(item.get("stance", "")).lower() == "support"
            )
            oppose_count = sum(
                1 for item in minister_positions.values() if str(item.get("stance", "")).lower() == "oppose"
            )
            neutral_count = max(total - support_count - oppose_count, 0)
        support_ratio = (support_count / total) if total else 0.0
        oppose_ratio = (oppose_count / total) if total else 0.0
        consensus_strength = max(support_ratio, oppose_ratio)
        dissent_level = 1.0 - consensus_strength if total else 1.0
        risk_flag = bool(council.get("red_line_concerns"))
        confidences: List[float] = []
        for item in minister_positions.values():
            try:
                confidences.append(float(item.get("confidence", 0.0)))
            except (TypeError, ValueError):
                continue
        confidence_mean = sum(confidences) / len(confidences) if confidences else 0.0
        council_signal = (
            0.5 * support_ratio
            + 0.3 * consensus_strength
            - 0.2 * dissent_level
        )
        if risk_flag:
            council_signal -= 0.2
        council_signal = max(0.0, min(1.0, council_signal))
        return {
            "support_ratio": round(support_ratio, 4),
            "consensus_strength": round(consensus_strength, 4),
            "dissent_level": round(dissent_level, 4),
            "risk_flag": bool(risk_flag),
            "confidence_mean": round(confidence_mean, 4),
            "minister_count": int(total),
            "council_signal": round(council_signal, 4),
        }

    @staticmethod
    def _extract_reasoning_budget(result: Any) -> int:
        request_context = getattr(result, "request_context_contract", None)
        if request_context is not None:
            routing_context = getattr(request_context, "routing_context", {}) or {}
            for key in ("reasoning_budget", "mode_controller_budget"):
                if key in routing_context:
                    return _safe_int(routing_context.get(key), default=0)
        return 0

    def _calibrate_confidence(self, confidence: float, routing_context: Optional[Mapping[str, Any]]) -> float:
        calibrator = self._get_probability_calibrator(routing_context)
        if calibrator is None:
            return confidence
        return calibrator.calibrate(float(confidence))

    def _get_probability_calibrator(
        self, routing_context: Optional[Mapping[str, Any]]
    ) -> Optional[ProbabilityCalibrator]:
        if not routing_context:
            return None
        temperature_path = routing_context.get("calibration_path") or routing_context.get("temperature_path")
        isotonic_path = routing_context.get("isotonic_path") or routing_context.get("isotonic_calibration_path")
        key = (str(temperature_path or ""), str(isotonic_path or ""))
        if key in self._calibration_cache:
            return self._calibration_cache[key]
        if not temperature_path and not isotonic_path:
            self._calibration_cache[key] = None
            return None
        try:
            calibrator = ProbabilityCalibrator.from_paths(
                Path(str(temperature_path)) if temperature_path else None,
                Path(str(isotonic_path)) if isotonic_path else None,
            )
        except Exception:
            calibrator = None
        self._calibration_cache[key] = calibrator
        return calibrator

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
        if isinstance(knowledge_result, Mapping):
            synthesized = (
                knowledge_result.get("synthesized_items")
                or knowledge_result.get("synthesized_knowledge")
                or []
            )
        else:
            synthesized = (
                getattr(knowledge_result, "synthesized_items", None)
                or getattr(knowledge_result, "synthesized_knowledge", None)
                or []
            )
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
            routing_context=self.routing_context,
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
                "confidence": item["era"].get("confidence_calibrated", item["era"]["confidence"]),
                "correct": bool(item["era"]["decision_correct"]),
            }
            for item in results
        ]
        budgets: List[int] = []
        for item in results:
            budget = item["era"].get("reasoning_budget")
            if budget is None:
                continue
            try:
                budgets.append(int(budget))
            except (TypeError, ValueError):
                continue
        era_accuracy = average(item["era"]["decision_correct"] for item in results)
        era_regret = average(item["era"]["regret"] for item in results)
        era_rubric = average(item["era"]["rubric_score"] for item in results)
        era_ece = expected_calibration_error(era_predictions)
        era_brier = brier_score(era_predictions)

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
                "brier_score": 0.0,
            }

        summary = {
            "scenario_count": len(results),
            "era": {
                "accuracy": round(era_accuracy, 4),
                "avg_regret": round(era_regret, 4),
                "rubric_score": round(era_rubric, 4),
                "ece": era_ece,
                "brier_score": era_brier,
                "avg_risk_score": round(average(item["era"].get("risk_score", 0.0) for item in results), 4),
            },
            "simulator": {
                "accuracy": round(simulator_accuracy, 4),
            },
            "baseline": baseline,
            "budget_distribution": _budget_distribution(budgets),
            "avg_budget": round(average(budgets), 4) if budgets else 0.0,
            "category_scores": {
                cat: round(average(values), 4) for cat, values in sorted(categories.items())
            },
            "results": results,
        }

        summary["budget_efficiency"] = aggregate_budget_metrics(
            results,
            cost_config=ComputeCostConfig(),
        )
        return summary


def _budget_distribution(budgets: List[int]) -> Dict[str, int]:
    distribution: Dict[str, int] = {}
    for budget in budgets:
        key = str(int(budget))
        distribution[key] = distribution.get(key, 0) + 1
    return distribution


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
