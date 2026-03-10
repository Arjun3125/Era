"""Training pipeline for the value model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import joblib

from modules.value_model.dataset_builder import build_dataset
from modules.value_model.feature_extractor import FeatureConfig, FeatureExtractor
from modules.value_model.model import ModelConfig, build_regressor


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
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], list[str], list[str]]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the decision value model.")
    parser.add_argument("--dataset", default="data/value_model/datasets/benchmark_v1.jsonl")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--output", default="data/value_model/model")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true", help="Use local-only sentence-transformers weights.")
    parser.add_argument("--model-type", default="mlp", help="mlp|ridge|random_forest")
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--rf-trees", type=int, default=200)
    parser.add_argument("--rf-max-depth", type=int, default=None)
    parser.add_argument("--rf-min-samples-leaf", type=int, default=2)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        build_dataset(
            scenarios_root=Path(args.scenarios_root),
            output_path=dataset_path,
        )

    rows = load_dataset(dataset_path)
    train_rows, test_rows, train_ids, test_ids = split_rows(
        rows,
        test_size=args.test_size,
        seed=args.seed,
    )

    y_train = np.array([float(row["score"]) for row in train_rows], dtype=float)
    y_test = np.array([float(row["score"]) for row in test_rows], dtype=float)

    prompt_texts = [row["prompt"] for row in train_rows]
    option_texts = [row["option"] for row in train_rows]

    feature_config = FeatureConfig(
        backend=args.backend,
        model_name=args.model_name,
        local_files_only=bool(args.st_local_only),
    )
    extractor = FeatureExtractor(config=feature_config)
    extractor.fit(prompt_texts, option_texts)

    X_train = build_features(extractor, train_rows)
    X_test = build_features(extractor, test_rows)

    model = build_regressor(
        ModelConfig(
            model_type=args.model_type,
            random_state=args.seed,
            ridge_alpha=args.ridge_alpha,
            rf_trees=args.rf_trees,
            rf_max_depth=args.rf_max_depth,
            rf_min_samples_leaf=args.rf_min_samples_leaf,
        )
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metrics = {
        "mse": float(mean_squared_error(y_test, preds)),
        "mae": float(mean_absolute_error(y_test, preds)),
        "r2": float(r2_score(y_test, preds)),
    }

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "value_model.pkl")
    extractor.save(output_dir)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_dir / "split.json").write_text(
        json.dumps(
            {
                "seed": args.seed,
                "test_size": args.test_size,
                "train_scenario_ids": train_ids,
                "test_scenario_ids": test_ids,
                "train_rows": len(train_rows),
                "test_rows": len(test_rows),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
