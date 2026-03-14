from __future__ import annotations

from modules.mode_controller.predictor import ModeControllerPredictor
from modules.reasoning_controller.predictor import ReasoningControllerPredictor


def test_reasoning_controller_fallback_and_overrides() -> None:
    predictor = ReasoningControllerPredictor()
    assert predictor.predict_budget("Prompt", {}) == 2

    overrides = ReasoningControllerPredictor.budget_overrides(0)
    assert overrides["disable_ministers"] is True
    assert overrides["requested_mode"] == "quick"

    overrides = ReasoningControllerPredictor.budget_overrides(2)
    assert overrides["expert_router_enabled"] is True
    assert overrides["expert_router_top_k"] == 4


def test_mode_controller_fallback_predicts_meeting() -> None:
    predictor = ModeControllerPredictor()
    assert predictor.predict_budget("Prompt", {}) == 1
    assert predictor.predict_mode("Prompt", {}) == "meeting"
