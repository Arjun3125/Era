"""Value model predictor for runtime scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import joblib

from .feature_extractor import FeatureExtractor


class ValueModelPredictor:
    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.model = joblib.load(self.model_dir / "value_model.pkl")
        self.extractor = FeatureExtractor.load(self.model_dir)

    def predict(self, prompt: str, option: str, context: Dict[str, Any]) -> float:
        features = self.extractor.encode(prompt, option, context)
        score = float(self.model.predict(np.asarray([features]))[0])
        return max(0.0, min(1.0, score))
