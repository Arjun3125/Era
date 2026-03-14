from __future__ import annotations

from dataclasses import dataclass

from modules.decision_engine.option_evaluator import OptionCandidate, OptionEvaluator
from modules.decision_simulator.engine import DecisionSimulator


def test_decision_simulator_scores_and_hints() -> None:
    simulator = DecisionSimulator()
    scenario = {
        "category": "strategy",
        "decision_options": ["lower price", "increase marketing", "ignore competitor"],
        "context": {"cash_reserve_months": 10, "time_pressure_days": 12},
    }
    utilities = simulator.compute_utilities(scenario)
    assert len(utilities) == 3
    best = simulator.choose_best(scenario)
    assert best.option in {"lower price", "increase marketing", "ignore competitor"}

    price_prediction = simulator.predict_outcome(scenario, "lower price")
    assert "price_war" in price_prediction.notes
    hints = simulator.reasoning_hints(scenario, price_prediction)
    assert isinstance(hints, list)


@dataclass
class _DecisionContract:
    decision: str
    confidence: float
    rationale: str


@dataclass
class _PackagingContract:
    recommendation: str
    red_line_count: int
    requires_followup: bool


@dataclass
class _ModeResolution:
    mode: str
    selected_ministers: list[str]


@dataclass
class _Result:
    decision_contract: _DecisionContract
    decision_packaging_contract: _PackagingContract
    mode_resolution: _ModeResolution
    run_id: str
    final_decision: dict
    council_result: dict


class _PipelineStub:
    def __init__(self, decision_map: dict[str, str]):
        self._decision_map = decision_map

    def run(self, *, user_input: str, requested_mode=None, routing_context=None, metadata=None, source=None):
        label = (metadata or {}).get("candidate_option")
        decision = self._decision_map.get(label, "defer")
        confidence = 0.85 if decision == "accept" else 0.2
        recommendation = "support" if decision == "accept" else "oppose"
        council_result = {
            "minister_positions": {
                "risk": {"stance": "support", "confidence": 0.7},
                "strategy": {"stance": "support", "confidence": 0.8},
            },
            "red_line_concerns": [],
        }
        return _Result(
            decision_contract=_DecisionContract(decision=decision, confidence=confidence, rationale="stub"),
            decision_packaging_contract=_PackagingContract(
                recommendation=recommendation,
                red_line_count=0,
                requires_followup=False,
            ),
            mode_resolution=_ModeResolution(mode="meeting", selected_ministers=["risk", "strategy"]),
            run_id="run-1",
            final_decision={"decision": decision},
            council_result=council_result,
        )


def test_option_evaluator_selects_best_candidate() -> None:
    pipeline = _PipelineStub({"A": "accept", "B": "reject"})
    evaluator = OptionEvaluator(
        pipeline=pipeline,
        decision_policy="reasoning_only",
    )
    candidates = [
        OptionCandidate(label="A", text="Increase marketing"),
        OptionCandidate(label="B", text="Ignore competitor"),
    ]
    best, evaluations = evaluator.evaluate(prompt="Scenario text", candidates=candidates)
    assert best.candidate.label == "A"
    assert len(evaluations) == 2


def test_option_evaluator_internal_scores() -> None:
    evaluator = OptionEvaluator(pipeline=_PipelineStub({}))
    metrics = evaluator._extract_council_metrics(
        _Result(
            decision_contract=_DecisionContract(decision="accept", confidence=0.7, rationale=""),
            decision_packaging_contract=_PackagingContract(
                recommendation="support", red_line_count=0, requires_followup=False
            ),
            mode_resolution=_ModeResolution(mode="meeting", selected_ministers=["risk"]),
            run_id="run-2",
            final_decision={},
            council_result={"minister_positions": {"risk": {"stance": "support", "confidence": 0.8}}},
        )
    )
    assert metrics["support_ratio"] == 1.0
    assert metrics["council_signal"] >= 0.0

    combined = evaluator._combine_scores(
        reasoning_score=0.4, policy_score=0.6, value_score=0.8, council_signal=0.2
    )
    assert 0.0 <= combined <= 1.0

    entropy = evaluator._policy_entropy({"A": 0.5, "B": 0.5})
    assert 0.9 <= entropy <= 1.0
    variance = evaluator._value_variance({"A": 0.5, "B": 0.7})
    assert variance == 0.01
