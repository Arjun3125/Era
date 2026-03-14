"""Training pipeline for the policy model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, log_loss, roc_auc_score

from modules.learning_core import FeatureConfig, FeatureExtractor, build_features, load_dataset, split_rows
from modules.policy_model.dataset_builder import build_dataset, build_dataset_from_simulated
from modules.policy_model.model import ModelConfig, build_classifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the decision policy model.")
    parser.add_argument("--dataset", default="data/policy_model/datasets/benchmark_v1_1.jsonl")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--simulated", default=None, help="Path to simulated JSONL dataset.")
    parser.add_argument("--output", default="data/policy_model/model")
    parser.add_argument("--backend", default="tfidf", help="tfidf|sentence_transformers|scenario_encoder")
    parser.add_argument("--model-name", default="", help="SentenceTransformer model name.")
    parser.add_argument("--st-local-only", action="store_true", help="Use local-only sentence-transformers weights.")
    parser.add_argument("--model-type", default="logistic", help="logistic|random_forest")
    parser.add_argument("--rf-trees", type=int, default=300)
    parser.add_argument("--rf-max-depth", type=int, default=None)
    parser.add_argument("--rf-min-samples-leaf", type=int, default=2)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if args.simulated:
        build_dataset_from_simulated(
            simulated_path=Path(args.simulated),
            output_path=dataset_path,
        )
    elif not dataset_path.exists():
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
    y_train = np.array([int(row["label"]) for row in train_rows], dtype=int)
    y_test = np.array([int(row["label"]) for row in test_rows], dtype=int)

    model = build_classifier(
        ModelConfig(
            model_type=args.model_type,
            random_state=args.seed,
            rf_trees=args.rf_trees,
            rf_max_depth=args.rf_max_depth,
            rf_min_samples_leaf=args.rf_min_samples_leaf,
        )
    )
    model.fit(X_train, y_train)

    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_test)[:, 1]
    else:
        scores = model.decision_function(X_test)
        probs = 1.0 / (1.0 + np.exp(-scores))
    preds = (probs >= 0.5).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_test, preds)),
        "f1": float(f1_score(y_test, preds, zero_division=0)),
        "log_loss": float(log_loss(y_test, probs, labels=[0, 1])),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_test, probs))
    except ValueError:
        metrics["roc_auc"] = 0.0

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "policy_model.pkl")
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
