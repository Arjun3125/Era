from modules.evaluation_engine import EvaluationRunner


def test_evaluation_runner_smoke():
    scenario = {
        "scenario_id": "SMOKE_001",
        "category": "strategy",
        "difficulty": "easy",
        "prompt": "A competitor dropped prices by 20%.",
        "context": {"company_size": "mid", "cash_reserve_months": 12},
        "decision_options": [
            "lower price",
            "add premium features",
        ],
        "expected_decision": "add premium features",
        "reasoning_rubric": ["avoid price war"],
        "evaluation": {"decision_weight": 0.5, "reasoning_weight": 0.5},
    }

    runner = EvaluationRunner(
        [scenario],
        decision_policy="hybrid_all",
        baseline_provider="none",
    )
    summary = runner.run()
    assert summary["scenario_count"] == 1
    assert "era" in summary
