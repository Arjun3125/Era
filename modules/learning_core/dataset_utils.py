"""Shared dataset utilities for learning models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.model_selection import train_test_split

from .feature_extractor import FeatureExtractor


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_features(extractor: FeatureExtractor, rows: List[Dict[str, Any]]) -> np.ndarray:
    features = [
        extractor.encode(row["prompt"], row["option"], row.get("context", {}))
        for row in rows
    ]
    return np.vstack(features)


def split_rows(
    rows: List[Dict[str, Any]],
    *,
    test_size: float,
    seed: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[str]]:
    scenario_ids = sorted({row.get("scenario_id", "") for row in rows if row.get("scenario_id")})
    if not scenario_ids:
        raise ValueError("No scenario_ids found in dataset rows.")

    train_ids, test_ids = train_test_split(
        scenario_ids, test_size=test_size, random_state=seed, shuffle=True
    )
    train_id_set = set(train_ids)
    test_id_set = set(test_ids)
    train_rows = [row for row in rows if row.get("scenario_id") in train_id_set]
    test_rows = [row for row in rows if row.get("scenario_id") in test_id_set]
    return train_rows, test_rows, sorted(train_id_set), sorted(test_id_set)
