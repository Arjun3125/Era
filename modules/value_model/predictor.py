"""Value model predictor for runtime scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import joblib

from modules.learning_core import FeatureExtractor


class ValueModelPredictor:
    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.model = joblib.load(self.model_dir / "value_model.pkl")
        self.extractor = FeatureExtractor.load(self.model_dir)

    def predict(self, prompt: str, option: str, context: Dict[str, Any]) -> float:
        features = self.extractor.encode(prompt, option, context)
        score = float(self.model.predict(np.asarray([features]))[0])
        return max(0.0, min(1.0, score))

    def warm_cache(self, prompt: str, options: list[str], context: Dict[str, Any]) -> None:
        if self.extractor.config.backend != "sentence_transformers":
            return
        prompt_text = self.extractor._format_prompt(prompt, context)
        option_texts = [str(item or "") for item in options]
        self.extractor.warm_cache([prompt_text], option_texts)
