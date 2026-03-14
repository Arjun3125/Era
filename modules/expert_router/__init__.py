"""Expert router for learned minister selection."""

from .expert_registry import EXPERTS, expert_weights_from_context
from .dataset_builder import build_dataset as build_router_dataset
from .router_model import RouterModelConfig, build_router_classifier
from .router_predictor import ExpertRouterPredictor
from .aggregator import aggregate_weighted_positions

__all__ = [
    "EXPERTS",
    "expert_weights_from_context",
    "build_router_dataset",
    "RouterModelConfig",
    "build_router_classifier",
    "ExpertRouterPredictor",
    "aggregate_weighted_positions",
]
