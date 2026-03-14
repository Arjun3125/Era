from __future__ import annotations

from modules.expert_router.aggregator import aggregate_weighted_positions
from modules.expert_router.expert_registry import expert_weights_from_context, normalize_experts
from modules.expert_router.router_model import RouterModelConfig, build_router_classifier
from modules.expert_router.router_predictor import ExpertRouterPredictor
from modules.moe_router.expert_manager import aggregate_scores, normalize_weights, select_top_k
from modules.moe_router.router_model import RouterModelConfig as MoEConfig, build_router_classifier as build_moe
from modules.moe_router.router_predictor import MoERouterPredictor


def test_expert_registry_weights_and_normalization() -> None:
    weights = expert_weights_from_context("Compliance risk exposure", {"domains": ["risk"]})
    assert "risk" in weights
    assert abs(sum(weights.values()) - 1.0) < 1e-6

    normalized = normalize_experts(["risk", "unknown", "strategy", "risk"])
    assert normalized == ["risk", "strategy"]


def test_weighted_aggregation_recommends_support() -> None:
    positions = {
        "risk": {"stance": "support", "confidence": 0.8},
        "strategy": {"stance": "support", "confidence": 0.7},
    }
    weights = {"risk": 0.6, "strategy": 0.4}
    result = aggregate_weighted_positions(positions, weights)
    assert result["recommendation"] == "support"
    assert result["consensus_strength"] > 0.0


def test_expert_router_predictor_fallback() -> None:
    predictor = ExpertRouterPredictor(model_dir=None)
    weights = predictor.predict("Budget allocation", {"domains": ["resource_allocation"]})
    assert weights
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_moe_expert_manager_utilities() -> None:
    weights = normalize_weights({"a": 1.0, "b": 2.0})
    assert weights == {"a": 0.3333, "b": 0.6667}
    top = select_top_k({"a": 0.1, "b": 0.4, "c": 0.2}, k=2)
    assert set(top.keys()) == {"b", "c"}
    score = aggregate_scores([("b", 0.8), ("c", 0.4)], top)
    assert score > 0.0


def test_moe_router_predictor_fallback() -> None:
    predictor = MoERouterPredictor(model_dir=None)
    weights = predictor.predict("Ethics privacy dilemma", {"domains": ["ethics"]})
    assert weights
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_router_model_builders() -> None:
    clf = build_router_classifier(RouterModelConfig())
    moe = build_moe(MoEConfig())
    assert clf is not None
    assert moe is not None
