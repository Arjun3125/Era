"""Smoke tests for MoE router predictor fallback behavior."""

from __future__ import annotations

from modules.moe_router import MoERouterPredictor


def test_moe_router_predictor_fallbacks_to_expert_weights():
    predictor = MoERouterPredictor()
    weights = predictor.predict("Sample scenario about risk and strategy.", {})
    assert isinstance(weights, dict)
    assert weights
    assert all(isinstance(value, float) for value in weights.values())
