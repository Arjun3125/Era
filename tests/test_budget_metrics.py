from modules.evaluation_engine.budget_metrics import (
    ComputeCostConfig,
    aggregate_budget_metrics,
    compute_cost,
    compute_efficiency,
    compute_quality,
)


def test_compute_cost_and_quality():
    config = ComputeCostConfig(budget_weight=0.5, minister_weight=0.2, base_cost=1.0)
    cost = compute_cost(2, 3, config)
    quality = compute_quality(1.0, 0.2, 0.3)
    efficiency = compute_efficiency(quality, cost)
    assert cost == 1.0 + 0.5 * 2 + 0.2 * 3
    assert quality == 1.0 - 0.2 + 0.3
    assert efficiency > 0.0


def test_aggregate_budget_metrics():
    results = [
        {
            "era": {
                "reasoning_budget": 0,
                "minister_count": 1,
                "decision_correct": 1,
                "regret": 0.0,
                "rubric_score": 0.2,
            }
        },
        {
            "era": {
                "reasoning_budget": 1,
                "minister_count": 2,
                "decision_correct": 0,
                "regret": 0.5,
                "rubric_score": 0.1,
            }
        },
    ]
    summary = aggregate_budget_metrics(results)
    assert "overall" in summary
    assert "by_budget" in summary
    assert summary["by_budget"]["0"]["count"] == 1.0
    assert summary["by_budget"]["1"]["count"] == 1.0
