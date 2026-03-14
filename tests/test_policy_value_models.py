from __future__ import annotations

from pathlib import Path

import numpy as np

from modules.learning_core.feature_extractor import FeatureConfig, FeatureExtractor
from modules.policy_model.model import ModelConfig as PolicyConfig, build_classifier
from modules.policy_model.predictor import PolicyModelPredictor
from modules.value_model.model import ModelConfig as ValueConfig, build_regressor
from modules.value_model.predictor import ValueModelPredictor


def _build_feature_extractor(tmp_path: Path) -> FeatureExtractor:
    extractor = FeatureExtractor(config=FeatureConfig(backend="tfidf"))
    extractor.fit(["Prompt A", "Prompt B"], ["Option A", "Option B"])
    extractor.save(tmp_path)
    return extractor


def test_policy_model_predictor_round_trip(tmp_path: Path) -> None:
    model_dir = tmp_path / "policy_model"
    extractor = _build_feature_extractor(model_dir)

    features = np.vstack(
        [
            extractor.encode("Prompt A", "Option A", {}),
            extractor.encode("Prompt B", "Option B", {}),
        ]
    )
    labels = np.array([1, 0], dtype=int)
    model = build_classifier(PolicyConfig(model_type="logistic", max_iter=200))
    model.fit(features, labels)

    import joblib

    joblib.dump(model, model_dir / "policy_model.pkl")
    predictor = PolicyModelPredictor(model_dir)
    score = predictor.predict("Prompt A", "Option A", {})
    assert 0.0 <= score <= 1.0


def test_value_model_predictor_round_trip(tmp_path: Path) -> None:
    model_dir = tmp_path / "value_model"
    extractor = _build_feature_extractor(model_dir)

    features = np.vstack(
        [
            extractor.encode("Prompt A", "Option A", {}),
            extractor.encode("Prompt B", "Option B", {}),
        ]
    )
    targets = np.array([0.8, 0.2], dtype=float)
    model = build_regressor(ValueConfig(model_type="ridge", ridge_alpha=1.0))
    model.fit(features, targets)

    import joblib

    joblib.dump(model, model_dir / "value_model.pkl")
    predictor = ValueModelPredictor(model_dir)
    score = predictor.predict("Prompt A", "Option A", {})
    assert 0.0 <= score <= 1.0
