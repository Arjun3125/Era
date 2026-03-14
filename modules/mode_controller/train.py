"""Train the adaptive mode controller."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

from modules.learning_core import FeatureConfig, FeatureExtractor, load_dataset, split_rows
from .controller_model import ModeControllerConfig, build_mode_controller_classifier
from .dataset_builder import build_dataset_from_runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Train adaptive mode controller.")
    parser.add_argument("--dataset", default="data/mode_controller/datasets/runs_v1.jsonl")
    parser.add_argument("--runs", default=None, help="Runs JSONL from controller data generation.")
    parser.add_argument("--output", default="data/mode_controller/model_v1")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true", help="Use local-only sentence-transformers weights.")
    parser.add_argument("--model-type", default="mlp", help="mlp|logistic")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if args.runs:
        build_dataset_from_runs(
            runs_path=Path(args.runs),
            output_path=dataset_path,
        )
    elif not dataset_path.exists():
        raise FileNotFoundError("Dataset not found and no --runs provided.")

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

    def build_features(rows: List[Dict[str, Any]]) -> np.ndarray:
        features = [
            extractor.encode(row["prompt"], "", row.get("context", {}))
            for row in rows
        ]
        return np.vstack(features)

    X_train = build_features(train_rows)
    X_test = build_features(test_rows)
    y_train = np.array([int(row["budget"]) for row in train_rows], dtype=int)
    y_test = np.array([int(row["budget"]) for row in test_rows], dtype=int)

    model = build_mode_controller_classifier(
        ModeControllerConfig(
            model_type=args.model_type,
            random_state=args.seed,
        )
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, preds)),
        "f1_macro": float(f1_score(y_test, preds, average="macro")),
    }

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "mode_controller.pkl")
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
