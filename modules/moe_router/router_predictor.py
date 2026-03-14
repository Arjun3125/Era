"""Predict expert routing weights via MoE router."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np

from modules.learning_core import FeatureExtractor
from modules.expert_router.expert_registry import EXPERTS, expert_weights_from_context

from .expert_manager import normalize_weights


class MoERouterPredictor:
    def __init__(self, model_dir: Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.model = None
        self.extractor = None
        self.experts = list(EXPERTS)

        if self.model_dir:
            model_path = self.model_dir / "router_model.pkl"
            if model_path.exists():
                self.model = joblib.load(model_path)
                self.extractor = FeatureExtractor.load(self.model_dir)
                experts_path = self.model_dir / "experts.json"
                if experts_path.exists():
                    self.experts = json.loads(experts_path.read_text(encoding="utf-8"))

    def predict(self, prompt: str, context: Dict[str, Any]) -> Dict[str, float]:
        if self.model is None or self.extractor is None:
            return expert_weights_from_context(prompt, context)

        features = self.extractor.encode(prompt, "", context)
        features_arr = np.asarray([features])
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(features_arr)
            if isinstance(probs, list):
                probs = np.asarray([p[:, 1] for p in probs]).T
        else:
            scores = self.model.decision_function(features_arr)
            probs = 1.0 / (1.0 + np.exp(-scores))
        weights = {
            str(expert): float(probs[0][idx])
            for idx, expert in enumerate(self.experts)
            if idx < len(probs[0])
        }
        return normalize_weights(weights)
