"""Predict reasoning budget and routing overrides."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np

from modules.learning_core import FeatureExtractor


class ReasoningControllerPredictor:
    def __init__(self, model_dir: Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.model = None
        self.extractor = None

        if self.model_dir:
            model_path = self.model_dir / "controller_model.pkl"
            if model_path.exists():
                self.model = joblib.load(model_path)
                self.extractor = FeatureExtractor.load(self.model_dir)

    def predict_budget(self, prompt: str, context: Dict[str, Any]) -> int:
        if self.model is None or self.extractor is None:
            return 2
        features = self.extractor.encode(prompt, "", context)
        pred = self.model.predict(np.asarray([features]))[0]
        try:
            return int(pred)
        except Exception:
            return 2

    @staticmethod
    def budget_overrides(budget: int) -> Dict[str, Any]:
        budget = int(budget)
        if budget <= 0:
            return {
                "disable_ministers": True,
                "requested_mode": "quick",
                "expert_router_enabled": False,
            }
        if budget == 1:
            return {
                "requested_mode": "meeting",
                "expert_router_enabled": True,
                "expert_router_top_k": 2,
            }
        if budget == 2:
            return {
                "requested_mode": "meeting",
                "expert_router_enabled": True,
                "expert_router_top_k": 4,
            }
        return {
            "requested_mode": "darbar",
            "expert_router_enabled": False,
        }

