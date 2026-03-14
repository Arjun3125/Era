"""Predict compute budget for adaptive mode selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np

from modules.learning_core import FeatureExtractor


class ModeControllerPredictor:
    _MODE_BY_BUDGET = {0: "quick", 1: "meeting", 2: "war", 3: "darbar"}

    def __init__(self, model_dir: Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.model = None
        self.extractor = None

        if self.model_dir:
            model_path = self.model_dir / "mode_controller.pkl"
            if model_path.exists():
                self.model = joblib.load(model_path)
                self.extractor = FeatureExtractor.load(self.model_dir)

    def predict_budget(self, prompt: str, context: Dict[str, Any]) -> int:
        if self.model is None or self.extractor is None:
            return 1
        features = self.extractor.encode(prompt, "", context)
        pred = self.model.predict(np.asarray([features]))[0]
        try:
            return int(pred)
        except Exception:
            return 1

    def predict_mode(self, prompt: str, context: Dict[str, Any]) -> str:
        budget = self.predict_budget(prompt, context)
        return self._MODE_BY_BUDGET.get(int(budget), "meeting")
