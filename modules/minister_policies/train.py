"""Train learned minister policies from scenario embeddings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np

from modules.representation import ScenarioEncoder, ScenarioEncoderConfig
from .dataset_builder import build_dataset, load_rows, filter_by_minister
from .policy_model import MinisterPolicyModel, PolicyConfig, STANCE_LABELS


def _build_embeddings(
    encoder: ScenarioEncoder,
    rows: List[Dict[str, any]],
) -> np.ndarray:
    vectors = [
        encoder.encode_scenario(
            prompt=row.get("prompt", ""),
            context=row.get("context", {}),
            knowledge=row.get("context", {}).get("synthesized_knowledge"),
        )
        for row in rows
    ]
    return np.vstack(vectors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train learned minister policies.")
    parser.add_argument("--scenarios-root", default="era_benchmark")
    parser.add_argument("--dataset", default="data/minister_policies/datasets/benchmark_v1_2.jsonl")
    parser.add_argument("--output", default="data/minister_policies")
    parser.add_argument("--model-name", default="all-MiniLM-L6-v2")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--hidden", default="64,32")
    parser.add_argument("--max-iter", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        build_dataset(
            scenarios_root=Path(args.scenarios_root),
            output_path=dataset_path,
        )

    rows = load_rows(dataset_path)
    ministers = sorted({str(row.get("minister", "")).strip().lower() for row in rows if row.get("minister")})

    encoder = ScenarioEncoder(
        ScenarioEncoderConfig(
            model_name=args.model_name,
            local_files_only=bool(args.local_only),
        )
    )

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    hidden_layers = tuple(int(x.strip()) for x in str(args.hidden).split(",") if x.strip())
    policy_config = PolicyConfig(hidden_layers=hidden_layers, max_iter=args.max_iter, random_state=args.seed)

    summary: Dict[str, Dict[str, float]] = {}
    for minister in ministers:
        minister_rows = filter_by_minister(rows, minister)
        if not minister_rows:
            continue
        X = _build_embeddings(encoder, minister_rows)
        y = [row.get("stance", "neutral") for row in minister_rows]

        model = MinisterPolicyModel(config=policy_config)
        model.fit(X, y)

        probs = model.predict_proba(X)
        stance_distribution = np.mean(probs, axis=0)
        summary[minister] = {
            label: float(score) for label, score in zip(STANCE_LABELS, stance_distribution)
        }

        minister_dir = output_root / minister
        minister_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, minister_dir / "policy.pkl")
        (minister_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "minister": minister,
                    "model_name": args.model_name,
                    "hidden_layers": list(hidden_layers),
                    "stance_priors": summary[minister],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
