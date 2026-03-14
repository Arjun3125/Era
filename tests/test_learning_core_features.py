from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from modules.learning_core.dataset_utils import load_dataset, split_rows
from modules.learning_core.feature_extractor import FeatureConfig, FeatureExtractor
from modules.learning_core.knowledge_features import (
    augment_context_with_knowledge,
    build_knowledge_features,
)


def test_feature_extractor_tfidf_fit_encode_save_load(tmp_path: Path) -> None:
    config = FeatureConfig(backend="tfidf")
    extractor = FeatureExtractor(config=config)
    prompts = ["Scenario one", "Scenario two"]
    options = ["Option A", "Option B"]
    extractor.fit(prompts, options)
    features = extractor.encode("Scenario one", "Option A", {"stakes": "medium"})
    assert features.shape[0] > 0

    model_dir = tmp_path / "features"
    extractor.save(model_dir)
    loaded = FeatureExtractor.load(model_dir)
    loaded_features = loaded.encode("Scenario one", "Option A", {"stakes": "medium"})
    assert loaded_features.shape == features.shape


def test_dataset_utils_load_and_split(tmp_path: Path) -> None:
    rows = [
        {"scenario_id": "S1", "prompt": "p1", "option": "a", "context": {}},
        {"scenario_id": "S2", "prompt": "p2", "option": "b", "context": {}},
        {"scenario_id": "S1", "prompt": "p1", "option": "c", "context": {}},
    ]
    path = tmp_path / "dataset.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    loaded = load_dataset(path)
    assert len(loaded) == 3

    train_rows, test_rows, train_ids, test_ids = split_rows(loaded, test_size=0.5, seed=42)
    assert train_rows and test_rows
    assert set(train_ids).isdisjoint(test_ids)


def test_split_rows_requires_scenario_ids() -> None:
    with pytest.raises(ValueError):
        split_rows([{"prompt": "x", "option": "y"}], test_size=0.2, seed=1)


def test_knowledge_feature_builder(monkeypatch) -> None:
    monkeypatch.setattr(
        "modules.learning_core.knowledge_features._load_principles",
        lambda: [
            {
                "text": "avoid single point of failure",
                "domain": "risk",
                "historical_success_rate": 0.8,
            }
        ],
    )
    features = build_knowledge_features("Single point of failure risk detected")
    assert features["knowledge_match_count"] == 1.0
    assert features["knowledge_avg_success_rate"] == 0.8
    assert features["knowledge_domain_risk"] == 1.0

    context = augment_context_with_knowledge({"stakes": "high"}, "risk detected")
    assert "knowledge_match_count" in context
