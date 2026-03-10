"""Train the council weight model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
from sklearn.metrics import mean_squared_error

from modules.learning_core import FeatureConfig, FeatureExtractor, build_features, load_dataset, split_rows
from modules.expert_router.expert_registry import EXPERTS
from .dataset_builder import build_dataset
from .weight_model import ModelConfig, build_regressor


def main() -> None:
    parser = argparse.ArgumentParser(description="Train council weight model.")
    parser.add_argument("--dataset", default="data/council_learning/datasets/benchmark_v1_1.jsonl")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--output", default="data/council_learning/model")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true", help="Use local-only sentence-transformers weights.")
    parser.add_argument("--model-type", default="mlp", help="mlp|ridge")
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
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

    prompt_texts = [row["prompt"] for row in train_rows]
    option_texts = ["" for _ in train_rows]
    feature_config = FeatureConfig(
        backend=args.backend,
        model_name=args.model_name,
        local_files_only=bool(args.st_local_only),
    )
    extractor = FeatureExtractor(config=feature_config)
    extractor.fit(prompt_texts, option_texts)

    X_train = build_features(extractor, train_rows)
    X_test = build_features(extractor, test_rows)
    y_train = np.array([row["weights"] for row in train_rows], dtype=float)
    y_test = np.array([row["weights"] for row in test_rows], dtype=float)

    model = build_regressor(
        ModelConfig(
            model_type=args.model_type,
            random_state=args.seed,
            ridge_alpha=args.ridge_alpha,
        )
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mse = float(mean_squared_error(y_test, preds))

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "weight_model.pkl")
    extractor.save(output_dir)
    (output_dir / "experts.json").write_text(json.dumps(list(EXPERTS), indent=2), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps({"mse": mse}, indent=2), encoding="utf-8")
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

    print(json.dumps({"mse": mse}, indent=2))


if __name__ == "__main__":
    main()
