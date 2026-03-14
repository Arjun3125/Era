"""Hybrid option evaluation that combines policy/value/council signals."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.decision_pipeline import DecisionPipelineEngine
from modules.policy_model import PolicyModelPredictor
from modules.value_model import ValueModelPredictor
from modules.learning_core import augment_context_with_knowledge
from modules.uncertainty import RiskModel


@dataclass
class OptionCandidate:
    label: str
    text: str
    title: str = ""
    description: str = ""


@dataclass
class OptionEvaluation:
    candidate: OptionCandidate
    final_score: float
    reasoning_score: float
    policy_score: float
    value_score: float
    council_signal: float
    decision: str
    recommendation: str
    confidence: float
    rationale: str
    red_line_count: int
    requires_followup: bool
    mode: str
    run_id: str
    selected_ministers: List[str]
    final_decision: Dict[str, Any]
    council_metrics: Dict[str, Any]


class OptionEvaluator:
    def __init__(
        self,
        *,
        pipeline: DecisionPipelineEngine,
        policy_model_path: str | None = None,
        value_model_path: str | None = None,
        decision_policy: str = "hybrid_all",
        policy_weight: float = 0.25,
        value_weight: float = 0.45,
        council_weight: float = 0.30,
        policy_top_k: Optional[int] = None,
    ) -> None:
        self.pipeline = pipeline
        self.policy_model = (
            PolicyModelPredictor(Path(policy_model_path))
            if policy_model_path
            else None
        )
        self.value_model = (
            ValueModelPredictor(Path(value_model_path))
            if value_model_path
            else None
        )
        self.decision_policy = str(decision_policy or "reasoning_only").strip().lower()
        self.policy_weight = float(policy_weight)
        self.value_weight = float(value_weight)
        self.council_weight = float(council_weight)
        self.policy_top_k = int(policy_top_k) if policy_top_k is not None else None

    def evaluate(
        self,
        *,
        prompt: str,
        candidates: List[OptionCandidate],
        context: Optional[Mapping[str, Any]] = None,
        requested_mode: Optional[str] = None,
        routing_context: Optional[Mapping[str, Any]] = None,
    ) -> tuple[OptionEvaluation, List[OptionEvaluation]]:
        if not candidates:
            raise ValueError("OptionEvaluator requires at least one candidate option.")

        base_context = dict(context or {})
        enriched_context = augment_context_with_knowledge(base_context, prompt)
        options = [candidate.text for candidate in candidates]

        if self.policy_model is not None:
            self.policy_model.warm_cache(prompt, options, enriched_context)
        if self.value_model is not None:
            self.value_model.warm_cache(prompt, options, enriched_context)

        policy_scores = self._compute_policy_scores(prompt, candidates, enriched_context)
        value_scores = self._compute_value_scores(prompt, candidates, enriched_context)
        policy_entropy = self._policy_entropy(policy_scores)
        value_variance = self._value_variance(value_scores)

        merged_routing = dict(routing_context or {})
        merged_routing.update(
            {
                "policy_entropy": policy_entropy,
                "value_variance": value_variance,
                "risk_score": RiskModel().score(
                    policy_entropy=policy_entropy,
                    value_variance=value_variance,
                    dissent_level=merged_routing.get("dissent_level"),
                ),
            }
        )

        candidate_pool = candidates
        if self.policy_top_k and policy_scores:
            ranked = sorted(
                candidates,
                key=lambda item: policy_scores.get(item.label, 0.0),
                reverse=True,
            )
            candidate_pool = ranked[: self.policy_top_k]

        evaluations: List[OptionEvaluation] = []
        if merged_routing.get("probe_minister"):
            self._run_probe_minister(prompt, candidates, merged_routing, requested_mode)
        for candidate in candidate_pool:
            result = self.pipeline.run(
                user_input=self._build_option_prompt(prompt, candidates, candidate),
                requested_mode=requested_mode,
                routing_context=merged_routing,
                metadata={
                    "candidate_option": candidate.label,
                    "candidate_text": candidate.text,
                },
                source="decision_engine",
            )
            decision = str(result.decision_contract.decision or "").strip().lower() or "defer"
            recommendation = (
                str(result.decision_packaging_contract.recommendation or "")
                .strip()
                .lower()
                or "defer"
            )
            confidence = float(result.decision_contract.confidence or 0.0)
            red_line_count = int(result.decision_packaging_contract.red_line_count or 0)
            requires_followup = bool(result.decision_packaging_contract.requires_followup)
            reasoning_score = self._score_reasoning(
                decision=decision,
                confidence=confidence,
                recommendation=recommendation,
                red_line_count=red_line_count,
                requires_followup=requires_followup,
            )
            council_metrics = self._extract_council_metrics(result)
            council_signal = council_metrics["council_signal"]
            policy_score = policy_scores.get(candidate.label, 0.0)
            value_score = value_scores.get(candidate.label, 0.0)
            final_score = self._combine_scores(
                reasoning_score=reasoning_score,
                policy_score=policy_score,
                value_score=value_score,
                council_signal=council_signal,
            )
            evaluations.append(
                OptionEvaluation(
                    candidate=candidate,
                    final_score=final_score,
                    reasoning_score=reasoning_score,
                    policy_score=policy_score,
                    value_score=value_score,
                    council_signal=council_signal,
                    decision=decision,
                    recommendation=recommendation,
                    confidence=confidence,
                    rationale=str(result.decision_contract.rationale or ""),
                    red_line_count=red_line_count,
                    requires_followup=requires_followup,
                    mode=str(result.mode_resolution.mode or requested_mode or "meeting"),
                    run_id=str(result.run_id),
                    selected_ministers=list(result.mode_resolution.selected_ministers or []),
                    final_decision=dict(result.final_decision or {}),
                    council_metrics=council_metrics,
                )
            )

        evaluations.sort(
            key=lambda item: (item.final_score, item.confidence, item.candidate.label),
            reverse=True,
        )
        return evaluations[0], evaluations

    def _run_probe_minister(
        self,
        prompt: str,
        candidates: List[OptionCandidate],
        routing_context: Dict[str, Any],
        requested_mode: Optional[str],
    ) -> None:
        if not candidates:
            return
        probe_minister = str(routing_context.get("probe_minister") or "risk").strip().lower()
        probe_label = str(routing_context.get("probe_label") or candidates[0].label).strip()
        probe_candidate = next(
            (candidate for candidate in candidates if candidate.label == probe_label),
            candidates[0],
        )
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
            user_input=self._build_option_prompt(prompt, candidates, probe_candidate),
            requested_mode=requested_mode or "meeting",
            routing_context=probe_context,
            metadata={
                "probe_minister": probe_minister,
                "probe_option": probe_candidate.label,
            },
            source="decision_engine_probe",
        )
        metrics = self._extract_council_metrics(result)
        routing_context["probe_support_ratio"] = metrics.get("support_ratio", 0.0)
        routing_context["probe_consensus_strength"] = metrics.get("consensus_strength", 0.0)
        routing_context["probe_confidence_mean"] = metrics.get("confidence_mean", 0.0)

    def _compute_policy_scores(
        self,
        prompt: str,
        candidates: Iterable[OptionCandidate],
        context: Mapping[str, Any],
    ) -> Dict[str, float]:
        if self.policy_model is None:
            return {}
        scores: Dict[str, float] = {}
        for candidate in candidates:
            scores[candidate.label] = self.policy_model.predict(
                prompt,
                candidate.text,
                context,
            )
        return scores

    def _compute_value_scores(
        self,
        prompt: str,
        candidates: Iterable[OptionCandidate],
        context: Mapping[str, Any],
    ) -> Dict[str, float]:
        if self.value_model is None:
            return {}
        scores: Dict[str, float] = {}
        for candidate in candidates:
            scores[candidate.label] = self.value_model.predict(
                prompt,
                candidate.text,
                context,
            )
        return scores

    def _combine_scores(
        self,
        *,
        reasoning_score: float,
        policy_score: float,
        value_score: float,
        council_signal: float,
    ) -> float:
        policy_weight = self.policy_weight if self.policy_model is not None else 0.0
        value_weight = self.value_weight if self.value_model is not None else 0.0
        council_weight = self.council_weight
        if self.decision_policy in {"hybrid_all", "hybrid"}:
            total = policy_weight + value_weight + council_weight
            if total <= 0:
                return reasoning_score
            return round(
                (value_weight * value_score + policy_weight * policy_score + council_weight * council_signal)
                / total,
                4,
            )
        if self.decision_policy in {"hybrid_policy_value"}:
            total = policy_weight + value_weight
            if total <= 0:
                return reasoning_score
            return round((value_weight * value_score + policy_weight * policy_score) / total, 4)
        if self.decision_policy in {"value_model", "hybrid_value"} and value_weight > 0:
            return round(value_score, 4)
        if self.decision_policy == "policy_model" and policy_weight > 0:
            return round(policy_score, 4)
        return reasoning_score

    @staticmethod
    def _score_reasoning(
        *,
        decision: str,
        confidence: float,
        recommendation: str,
        red_line_count: int,
        requires_followup: bool,
    ) -> float:
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

    @staticmethod
    def _build_option_prompt(
        prompt: str,
        candidates: List[OptionCandidate],
        candidate: OptionCandidate,
    ) -> str:
        labeled = [f"{item.label}. {item.text}" for item in candidates]
        options = "\n".join(labeled)
        return "\n".join(
            [
                "Scenario:",
                prompt,
                "",
                "Options:",
                options,
                "",
                "Evaluate the following option:",
                f"Option: {candidate.text}",
                "Explain pros and cons.",
                "Return score from 0-1.",
            ]
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
