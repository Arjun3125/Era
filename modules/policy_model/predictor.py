"""Policy model predictor for runtime scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np

from modules.learning_core import FeatureExtractor


class PolicyModelPredictor:
    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.model = joblib.load(self.model_dir / "policy_model.pkl")
        self.extractor = FeatureExtractor.load(self.model_dir)

    def predict(self, prompt: str, option: str, context: Dict[str, Any]) -> float:
        features = self.extractor.encode(prompt, option, context)
        features_arr = np.asarray([features])
        if hasattr(self.model, "predict_proba"):
            prob = float(self.model.predict_proba(features_arr)[0][1])
            return max(0.0, min(1.0, prob))
        if hasattr(self.model, "decision_function"):
            score = float(self.model.decision_function(features_arr)[0])
            prob = 1.0 / (1.0 + np.exp(-score))
            return max(0.0, min(1.0, prob))
        return float(self.model.predict(features_arr)[0])

    def warm_cache(self, prompt: str, options: list[str], context: Dict[str, Any]) -> None:
        if self.extractor.config.backend != "sentence_transformers":
            return
        prompt_text = self.extractor._format_prompt(prompt, context)
        option_texts = [str(item or "") for item in options]
        self.extractor.warm_cache([prompt_text], option_texts)
