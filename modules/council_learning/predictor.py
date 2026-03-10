"""Predict minister weights for council aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np

from modules.learning_core import FeatureExtractor
from modules.expert_router.expert_registry import EXPERTS, expert_weights_from_context


class CouncilWeightPredictor:
    def __init__(self, model_dir: Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.model = None
        self.extractor = None
        self.experts = list(EXPERTS)

        if self.model_dir:
            model_path = self.model_dir / "weight_model.pkl"
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
        preds = np.asarray(self.model.predict(np.asarray([features]))[0], dtype=float)
        preds = np.clip(preds, 0.0, None)
        total = float(preds.sum()) or 1.0
        return {
            str(expert): round(float(preds[idx] / total), 4)
            for idx, expert in enumerate(self.experts)
            if idx < len(preds)
        }
