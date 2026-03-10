"""Hyperparameter sweep for the value model on ERA-Bench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.value_model.dataset_builder import build_dataset
from modules.value_model.feature_extractor import FeatureConfig, FeatureExtractor
from modules.value_model.model import ModelConfig, build_regressor
from modules.value_model.train import build_features, load_dataset, split_rows


def evaluate(
    model_config: ModelConfig,
    *,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> Dict[str, float]:
    model = build_regressor(model_config)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    return {
        "mse": float(mean_squared_error(y_test, preds)),
        "mae": float(mean_absolute_error(y_test, preds)),
        "r2": float(r2_score(y_test, preds)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune value model hyperparameters.")
    parser.add_argument("--dataset", default="data/value_model/datasets/benchmark_v1_1.jsonl")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--output", default="data/value_model/tuning_v1_1")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true", help="Use local-only sentence-transformers weights.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
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
    y_train = np.array([float(row["score"]) for row in train_rows], dtype=float)
    y_test = np.array([float(row["score"]) for row in test_rows], dtype=float)

    configs: List[ModelConfig] = []
    for alpha in (0.1, 1.0, 10.0):
        configs.append(ModelConfig(model_type="ridge", ridge_alpha=alpha, random_state=args.seed))
    for trees in (200, 400):
        for depth in (None, 8):
            configs.append(
                ModelConfig(
                    model_type="random_forest",
                    rf_trees=trees,
                    rf_max_depth=depth,
                    rf_min_samples_leaf=2,
                    random_state=args.seed,
                )
            )

    results = []
    best = None
    for config in configs:
        metrics = evaluate(
            config,
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
        )
        entry = {
            "model_type": config.model_type,
            "ridge_alpha": config.ridge_alpha,
            "rf_trees": config.rf_trees,
            "rf_max_depth": config.rf_max_depth,
            "rf_min_samples_leaf": config.rf_min_samples_leaf,
            "metrics": metrics,
        }
        results.append(entry)
        if best is None or metrics["mse"] < best["metrics"]["mse"]:
            best = entry

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "tuning_results.json").write_text(
        json.dumps(
            {
                "seed": args.seed,
                "test_size": args.test_size,
                "backend": args.backend,
                "model_name": args.model_name,
                "results": results,
                "best": best,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if best is None:
        raise RuntimeError("No tuning results produced.")

    best_config = ModelConfig(
        model_type=best["model_type"],
        ridge_alpha=best["ridge_alpha"],
        rf_trees=best["rf_trees"],
        rf_max_depth=best["rf_max_depth"],
        rf_min_samples_leaf=best["rf_min_samples_leaf"],
        random_state=args.seed,
    )
    best_model = build_regressor(best_config)
    best_model.fit(X_train, y_train)

    best_dir = output_root / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, best_dir / "value_model.pkl")
    extractor.save(best_dir)
    (best_dir / "metrics.json").write_text(json.dumps(best["metrics"], indent=2), encoding="utf-8")
    (best_dir / "split.json").write_text(
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

    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
