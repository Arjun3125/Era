"""Train the expert router model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score

from modules.learning_core import FeatureConfig, FeatureExtractor, load_dataset, split_rows
from .dataset_builder import build_dataset
from .expert_registry import EXPERTS
from .router_model import RouterModelConfig, build_router_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Train expert router model.")
    parser.add_argument("--dataset", default="data/expert_router/datasets/benchmark_v2.jsonl")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--output", default="data/expert_router/model_v2")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true", help="Use local-only sentence-transformers weights.")
    parser.add_argument("--model-type", default="logistic", help="logistic|random_forest")
    parser.add_argument("--label-threshold", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        build_dataset(
            scenarios_root=Path(args.scenarios_root),
            output_path=dataset_path,
            label_threshold=args.label_threshold,
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

    def build_features(rows: List[Dict[str, Any]]) -> np.ndarray:
        features = [
            extractor.encode(row["prompt"], "", row.get("context", {}))
            for row in rows
        ]
        return np.vstack(features)

    X_train = build_features(train_rows)
    X_test = build_features(test_rows)
    y_train = np.array([row["labels"] for row in train_rows], dtype=int)
    y_test = np.array([row["labels"] for row in test_rows], dtype=int)

    model = build_router_classifier(
        RouterModelConfig(
            model_type=args.model_type,
            random_state=args.seed,
        )
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metrics = {
        "f1_micro": float(f1_score(y_test, preds, average="micro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, preds, average="macro", zero_division=0)),
        "precision_micro": float(precision_score(y_test, preds, average="micro", zero_division=0)),
        "recall_micro": float(recall_score(y_test, preds, average="micro", zero_division=0)),
    }

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "router_model.pkl")
    extractor.save(output_dir)
    (output_dir / "experts.json").write_text(json.dumps(list(EXPERTS), indent=2), encoding="utf-8")
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
