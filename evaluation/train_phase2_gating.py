#!/usr/bin/env python
"""
Train minister-weight gating network offline.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from evaluation.gating_model import (
    GatingTrainingConfig,
    save_gating_bundle,
    train_gating_model,
)
from evaluation.gating_support import fit_pca_reducer, apply_pca_reducer


def _load_rows(path: str) -> List[Dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if not rows:
        raise ValueError(f"No rows found in dataset: {path}")
    return rows


def _row_structured_input(row: Dict[str, Any]) -> List[float]:
    if "gating_input_structured" in row and isinstance(row["gating_input_structured"], list):
        return [float(v) for v in row["gating_input_structured"]]
    if "gating_input_50" in row and isinstance(row["gating_input_50"], list):
        return [float(v) for v in row["gating_input_50"]]
    raise KeyError("Row missing gating_input_structured/gating_input_50")


def _prepare_model_inputs(
    train_rows: List[Dict[str, Any]],
    val_rows: List[Dict[str, Any]],
    *,
    use_embeddings: bool,
    embedding_reduced_dim: int,
    pca_seed: int,
    embedding_model: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    train_rows = [dict(r) for r in train_rows]
    val_rows = [dict(r) for r in val_rows]

    reducer: Dict[str, Any] = {}
    if use_embeddings:
        train_emb = [r.get("scenario_embedding_raw", []) for r in train_rows]
        if not train_emb or not isinstance(train_emb[0], list) or not train_emb[0]:
            raise ValueError("Embeddings requested but train dataset has no scenario_embedding_raw vectors.")
        reducer = fit_pca_reducer(
            [[float(x) for x in v] for v in train_emb],
            output_dim=embedding_reduced_dim,
            seed=pca_seed,
        )

    def _attach(rows: List[Dict[str, Any]]) -> None:
        for r in rows:
            structured = _row_structured_input(r)
            model_input = list(structured)
            if use_embeddings:
                raw = [float(x) for x in (r.get("scenario_embedding_raw", []) or [])]
                reduced = apply_pca_reducer(raw, reducer)
                if len(reduced) < embedding_reduced_dim:
                    reduced += [0.0] * (embedding_reduced_dim - len(reduced))
                elif len(reduced) > embedding_reduced_dim:
                    reduced = reduced[:embedding_reduced_dim]
                model_input.extend(reduced)
            r["model_input"] = model_input

    _attach(train_rows)
    _attach(val_rows)
    input_dim = len(train_rows[0]["model_input"])
    feature_spec = {
        "input_dim": input_dim,
        "include_extended_features": True,
        "use_embeddings": bool(use_embeddings),
        "embedding_model": embedding_model if use_embeddings else None,
        "embedding_reduced_dim": embedding_reduced_dim if use_embeddings else 0,
        "embedding_timeout_sec": 20.0,
        "embedding_pca_reducer": reducer if use_embeddings else {},
        "structured_dim": len(_row_structured_input(train_rows[0])),
    }
    return train_rows, val_rows, feature_spec


def _hyper_grid(args: argparse.Namespace, input_dim: int) -> List[GatingTrainingConfig]:
    lrs = [float(x) for x in args.lr_grid.split(",")]
    ents = [float(x) for x in args.entropy_grid.split(",")]
    prior_regs = [float(x) for x in args.prior_reg_grid.split(",")]
    cfgs = []
    for lr in lrs:
        for ent in ents:
            for prior_reg in prior_regs:
                cfgs.append(
                    GatingTrainingConfig(
                        input_dim=input_dim,
                        hidden_dim=args.hidden_dim,
                        stage1_epochs=args.stage1_epochs,
                        stage2_epochs=args.stage2_epochs,
                        lr=lr,
                        weight_decay=args.weight_decay,
                        entropy_reg=ent,
                        prior_reg=prior_reg,
                        calibration_brier_weight=args.calibration_brier_weight,
                        regret_weight_alpha=args.regret_weight_alpha,
                        seed=args.seed,
                        early_stop_patience=args.early_stop_patience,
                    )
                )
    return cfgs


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Phase2 minister gating model")
    parser.add_argument("--train-dataset", default="evaluation/results/gating_dataset_train.json")
    parser.add_argument("--val-dataset", default="evaluation/results/gating_dataset_val.json")
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--stage1-epochs", type=int, default=60)
    parser.add_argument("--stage2-epochs", type=int, default=250)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--early-stop-patience", type=int, default=30)
    parser.add_argument("--lr-grid", default="0.001,0.0005")
    parser.add_argument("--entropy-grid", default="0.01,0.02")
    parser.add_argument("--prior-reg-grid", default="0.01,0.02")
    parser.add_argument("--calibration-brier-weight", type=float, default=0.1)
    parser.add_argument("--regret-weight-alpha", type=float, default=1.0)
    parser.add_argument("--use-embeddings", action="store_true")
    parser.add_argument("--embedding-reduced-dim", type=int, default=64)
    parser.add_argument("--embedding-model", default="nomic-embed-text:latest")
    parser.add_argument(
        "--output-model",
        default="evaluation/models/phase2_gating_model.pt",
    )
    parser.add_argument(
        "--output-meta",
        default="evaluation/models/phase2_gating_model.meta.json",
    )
    parser.add_argument(
        "--output-report",
        default="evaluation/results/phase2_gating_training_report.json",
    )
    args = parser.parse_args()

    train_rows = _load_rows(args.train_dataset)
    val_rows = _load_rows(args.val_dataset)
    minister_order = train_rows[0]["minister_order"]
    feature_names_41 = [f"f{i:02d}" for i in range(41)]

    if len(train_rows) < 300:
        print(f"[WARN] Train rows are low for routing model: {len(train_rows)} (target >= 300).")

    train_rows_prepped, val_rows_prepped, feature_spec = _prepare_model_inputs(
        train_rows,
        val_rows,
        use_embeddings=bool(args.use_embeddings),
        embedding_reduced_dim=int(args.embedding_reduced_dim),
        pca_seed=int(args.seed),
        embedding_model=str(args.embedding_model),
    )

    input_dim = len(train_rows_prepped[0]["model_input"])
    best = None

    for cfg in _hyper_grid(args, input_dim=input_dim):
        model, report = train_gating_model(
            train_records=train_rows_prepped,
            val_records=val_rows_prepped,
            minister_order=minister_order,
            config=cfg,
        )
        metric = float(report["best_val_loss"])
        if best is None or metric < best["best_val_loss"]:
            best = {
                "model": model,
                "report": report,
                "config": cfg,
                "best_val_loss": metric,
            }

    if best is None:
        raise RuntimeError("No training run completed.")

    save_gating_bundle(
        model=best["model"],
        minister_order=minister_order,
        feature_names_41=feature_names_41,
        output_model_path=args.output_model,
        output_meta_path=args.output_meta,
        training_report=best["report"],
        config=best["config"],
        feature_spec=feature_spec,
    )

    report_payload = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "train_dataset": args.train_dataset,
        "val_dataset": args.val_dataset,
        "n_train_rows": len(train_rows_prepped),
        "n_val_rows": len(val_rows_prepped),
        "selected_config": {
            "input_dim": best["config"].input_dim,
            "hidden_dim": best["config"].hidden_dim,
            "stage1_epochs": best["config"].stage1_epochs,
            "stage2_epochs": best["config"].stage2_epochs,
            "lr": best["config"].lr,
            "weight_decay": best["config"].weight_decay,
            "entropy_reg": best["config"].entropy_reg,
            "prior_reg": best["config"].prior_reg,
            "calibration_brier_weight": best["config"].calibration_brier_weight,
            "regret_weight_alpha": best["config"].regret_weight_alpha,
            "seed": best["config"].seed,
            "early_stop_patience": best["config"].early_stop_patience,
        },
        "feature_spec": feature_spec,
        "training_report": best["report"],
        "output_model": args.output_model,
        "output_meta": args.output_meta,
    }

    out = Path(args.output_report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    print(f"Saved gating model: {args.output_model}")
    print(f"Saved gating meta: {args.output_meta}")
    print(f"Saved training report: {out}")
    print(f"Best validation loss: {best['best_val_loss']:.6f}")


if __name__ == "__main__":
    main()
