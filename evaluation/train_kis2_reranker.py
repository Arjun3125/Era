#!/usr/bin/env python
"""
Train a lightweight KIS2 principle reranker.

Expected input JSON rows (list):
{
  "similarity_score": float,
  "irreversibility_score": float,
  "disagreement_entropy": float,
  "domain_match": float,
  "historical_success_rate": float,
  "scenario_category": float,
  "label": 0 or 1
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
import torch.nn as nn


FEATURES = [
    "similarity_score",
    "irreversibility_score",
    "disagreement_entropy",
    "domain_match",
    "historical_success_rate",
    "scenario_category",
]


class Reranker(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def _to_matrix(rows: List[Dict]) -> tuple[np.ndarray, np.ndarray]:
    xs: List[List[float]] = []
    ys: List[float] = []
    for row in rows:
        if "label" not in row:
            continue
        x = [float(row.get(name, 0.0)) for name in FEATURES]
        y = float(row.get("label", 0.0))
        xs.append(x)
        ys.append(y)
    if not xs:
        raise ValueError("No valid rows found in reranker training data.")
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train KIS2 reranker model")
    parser.add_argument("--train-json", required=True, help="Training rows JSON path")
    parser.add_argument(
        "--output-json",
        default="evaluation/models/kis2_reranker_v1.json",
        help="Output reranker artifact JSON",
    )
    parser.add_argument("--hidden-dim", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    rows = json.loads(Path(args.train_json).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Training JSON must be a list of rows.")
    x_np, y_np = _to_matrix(rows)

    x = torch.from_numpy(x_np)
    y = torch.from_numpy(y_np)
    model = Reranker(in_dim=x.shape[1], hidden_dim=int(args.hidden_dim))
    opt = torch.optim.AdamW(model.parameters(), lr=float(args.lr), weight_decay=float(args.weight_decay))
    loss_fn = nn.BCEWithLogitsLoss()

    model.train()
    for _ in range(int(args.epochs)):
        opt.zero_grad(set_to_none=True)
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(x)).cpu().numpy()
    pred = (probs >= 0.5).astype(np.float32)
    acc = float((pred == y_np).mean())

    state = {k: v.detach().cpu().tolist() for k, v in model.state_dict().items()}
    out_payload = {
        "artifact": {
            "type": "kis2_reranker_v1",
            "feature_names": list(FEATURES),
            "state_dict": state,
        },
        "training": {
            "rows": int(x_np.shape[0]),
            "hidden_dim": int(args.hidden_dim),
            "epochs": int(args.epochs),
            "lr": float(args.lr),
            "weight_decay": float(args.weight_decay),
            "seed": int(args.seed),
            "train_accuracy": float(acc),
        },
    }

    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    print(f"[KIS2] Saved reranker artifact: {out}")
    print(f"[KIS2] Train rows={x_np.shape[0]} accuracy={acc:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
