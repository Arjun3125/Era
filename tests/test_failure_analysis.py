import pytest

from modules.failure_analysis import analyze_traces
from modules.failure_analysis.error_categories import FailureCategoryConfig, classify_failure


def test_classify_failure_categories():
    trace = {
        "model_decision": "launch_now",
        "expected_decision": "delay_launch",
        "policy_probabilities": {"launch_now": 0.8, "delay_launch": 0.2},
        "value_scores": {"launch_now": 0.3, "delay_launch": 0.6},
        "council_signal": {"consensus_strength": 0.2},
        "confidence": 0.85,
        "budget": 2,
        "policy_entropy": 0.1,
        "value_variance": 0.1,
    }

    categories = classify_failure(
        trace,
        FailureCategoryConfig(
            policy_confidence_threshold=0.7,
            value_margin=0.05,
            consensus_threshold=0.3,
            overconfidence_threshold=0.7,
            high_budget_threshold=2,
            low_uncertainty_threshold=0.2,
        ),
    )

    assert "policy_overconfidence" in categories
    assert "value_misprediction" in categories
    assert "council_disagreement" in categories
    assert "uncertainty_overconfidence" in categories
    assert "controller_budget_error" in categories


def test_analyze_traces_summary():
    traces = [
        {
            "scenario_id": "S1",
            "category": "strategy",
            "model_decision": "accept",
            "expected_decision": "accept",
            "decision_correct": 1,
            "regret": 0.0,
        },
        {
            "scenario_id": "S2",
            "category": "risk",
            "model_decision": "reject",
            "expected_decision": "accept",
            "decision_correct": 0,
            "regret": 0.5,
        },
    ]

    analysis = analyze_traces(traces, top_k=5)
    assert analysis.total == 2
    assert analysis.failures == 1
    assert analysis.failure_rate == pytest.approx(0.5, rel=1e-3)
    assert analysis.category_accuracy["risk"] == 0.0
    assert analysis.category_accuracy["strategy"] == 1.0
