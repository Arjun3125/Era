"""
PyTorch gating network for minister weighting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class GatingTrainingConfig:
    input_dim: int = 50
    hidden_dim: int = 64
    stage1_epochs: int = 60
    stage2_epochs: int = 250
    lr: float = 1e-3
    weight_decay: float = 1e-4
    entropy_reg: float = 1e-2
    prior_reg: float = 1e-2
    calibration_brier_weight: float = 0.1
    regret_weight_alpha: float = 1.0
    seed: int = 42
    early_stop_patience: int = 30
    prior_weights: Sequence[float] | None = None


class MinisterGatingMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_ministers: int):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, num_ministers)

    def logits(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(F.relu(self.fc1(x)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.softmax(self.logits(x), dim=-1)


def _record_input(record: Dict[str, Any]) -> List[float]:
    if "model_input" in record and isinstance(record["model_input"], list):
        return [float(v) for v in record["model_input"]]
    if "gating_input_50" in record and isinstance(record["gating_input_50"], list):
        return [float(v) for v in record["gating_input_50"]]
    raise KeyError("Record missing model_input/gating_input_50")


def _stack_records(
    records: Sequence[Dict[str, Any]],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    x = torch.tensor([_record_input(r) for r in records], dtype=torch.float32)
    minister_scores = torch.tensor([r["minister_score_vector"] for r in records], dtype=torch.float32)
    y = torch.tensor([r["target_regret_adjusted_outcome"] for r in records], dtype=torch.float32)
    y = torch.clamp(y, 1e-5, 1 - 1e-5)
    best_idx = torch.argmax(minister_scores, dim=1).long()
    return x, minister_scores, y, best_idx


def _prior_tensor(config: GatingTrainingConfig, num_ministers: int, device: torch.device) -> torch.Tensor:
    if config.prior_weights:
        p = torch.tensor([float(v) for v in config.prior_weights], dtype=torch.float32, device=device)
        if p.numel() != num_ministers:
            raise ValueError("prior_weights length must match num_ministers")
        p = torch.clamp(p, min=1e-6)
        return p / p.sum()
    return torch.full((num_ministers,), 1.0 / num_ministers, dtype=torch.float32, device=device)


def _stage2_loss_terms(
    model: MinisterGatingMLP,
    x: torch.Tensor,
    minister_scores: torch.Tensor,
    y: torch.Tensor,
    config: GatingTrainingConfig,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    weights = model(x)
    y_hat = torch.sum(weights * minister_scores, dim=1)
    y_hat = torch.clamp(y_hat, 1e-5, 1 - 1e-5)

    sample_weight = 1.0 + config.regret_weight_alpha * (1.0 - y)
    bce_each = F.binary_cross_entropy(y_hat, y, reduction="none")
    wbce = (sample_weight * bce_each).mean()
    brier = torch.mean((y_hat - y) ** 2)
    entropy = -(weights * torch.log(weights + 1e-9)).sum(dim=1).mean()
    prior = _prior_tensor(config, weights.shape[1], weights.device)
    kl_to_prior = (weights * (torch.log(weights + 1e-9) - torch.log(prior.unsqueeze(0) + 1e-9))).sum(dim=1).mean()

    loss = (
        wbce
        + config.calibration_brier_weight * brier
        + config.entropy_reg * (-entropy)
        + config.prior_reg * kl_to_prior
    )
    stats = {
        "loss": float(loss.detach().cpu().item()),
        "wbce": float(wbce.detach().cpu().item()),
        "brier": float(brier.detach().cpu().item()),
        "entropy": float(entropy.detach().cpu().item()),
        "kl_to_prior": float(kl_to_prior.detach().cpu().item()),
        "y_hat_mean": float(y_hat.detach().cpu().mean().item()),
    }
    return loss, stats


def _eval_stage2(
    model: MinisterGatingMLP,
    x: torch.Tensor,
    minister_scores: torch.Tensor,
    y: torch.Tensor,
    config: GatingTrainingConfig,
) -> Dict[str, float]:
    model.eval()
    with torch.no_grad():
        loss, stats = _stage2_loss_terms(model, x, minister_scores, y, config)
    return {"loss": float(loss.cpu().item()), **stats}


def _weight_collapse_stats(model: MinisterGatingMLP, x: torch.Tensor) -> Dict[str, Any]:
    model.eval()
    with torch.no_grad():
        w = model(x).cpu()
    mean_weights = w.mean(dim=0).tolist()
    max_mean = float(max(mean_weights)) if mean_weights else 0.0
    argmax = w.argmax(dim=1)
    counts: Dict[str, int] = {}
    for idx in argmax.tolist():
        key = str(idx)
        counts[key] = counts.get(key, 0) + 1
    return {
        "mean_weights_by_index": mean_weights,
        "max_mean_weight": max_mean,
        "argmax_counts_by_index": counts,
        "n_samples": int(w.shape[0]),
    }


def train_gating_model(
    *,
    train_records: Sequence[Dict[str, Any]],
    val_records: Sequence[Dict[str, Any]],
    minister_order: Sequence[str],
    config: GatingTrainingConfig,
) -> Tuple[MinisterGatingMLP, Dict[str, Any]]:
    if not train_records:
        raise ValueError("No training records provided.")
    if not val_records:
        raise ValueError("No validation records provided.")

    torch.manual_seed(config.seed)
    x_tr, m_tr, y_tr, best_tr = _stack_records(train_records)
    x_va, m_va, y_va, best_va = _stack_records(val_records)

    model = MinisterGatingMLP(
        input_dim=config.input_dim,
        hidden_dim=config.hidden_dim,
        num_ministers=len(minister_order),
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.lr,
        weight_decay=config.weight_decay,
    )

    stage1_history: List[Dict[str, float]] = []
    for epoch in range(1, config.stage1_epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model.logits(x_tr)
        ce = F.cross_entropy(logits, best_tr)
        ce.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            tr_acc = float((torch.argmax(model.logits(x_tr), dim=1) == best_tr).float().mean().item())
            va_acc = float((torch.argmax(model.logits(x_va), dim=1) == best_va).float().mean().item())
        stage1_history.append(
            {
                "epoch": float(epoch),
                "cross_entropy": float(ce.detach().cpu().item()),
                "train_best_minister_acc": tr_acc,
                "val_best_minister_acc": va_acc,
            }
        )

    best_state = None
    best_val = float("inf")
    best_epoch = -1
    patience = 0
    stage2_history: List[Dict[str, float]] = []

    for epoch in range(1, config.stage2_epochs + 1):
        model.train()
        optimizer.zero_grad()
        loss, train_stats = _stage2_loss_terms(model, x_tr, m_tr, y_tr, config)
        loss.backward()
        optimizer.step()

        val_stats = _eval_stage2(model, x_va, m_va, y_va, config)
        record = {
            "epoch": float(epoch),
            "train_loss": train_stats["loss"],
            "val_loss": val_stats["loss"],
            "train_wbce": train_stats["wbce"],
            "val_wbce": val_stats["wbce"],
            "val_brier": val_stats["brier"],
            "val_entropy": val_stats["entropy"],
            "val_kl_to_prior": val_stats["kl_to_prior"],
        }
        stage2_history.append(record)

        if val_stats["loss"] < best_val - 1e-8:
            best_val = val_stats["loss"]
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
            if patience >= config.early_stop_patience:
                break

    if best_state is None:
        raise RuntimeError("Training failed to produce a valid model state.")
    model.load_state_dict(best_state)

    train_eval = _eval_stage2(model, x_tr, m_tr, y_tr, config)
    val_eval = _eval_stage2(model, x_va, m_va, y_va, config)
    collapse = _weight_collapse_stats(model, x_tr)
    model.eval()
    with torch.no_grad():
        train_best_acc = float((torch.argmax(model.logits(x_tr), dim=1) == best_tr).float().mean().item())
        val_best_acc = float((torch.argmax(model.logits(x_va), dim=1) == best_va).float().mean().item())

    report = {
        "best_stage2_epoch": best_epoch,
        "best_val_loss": best_val,
        "train_eval": train_eval,
        "val_eval": val_eval,
        "stage1_final_train_best_minister_acc": train_best_acc,
        "stage1_final_val_best_minister_acc": val_best_acc,
        "weight_collapse": collapse,
        "stage1_history": stage1_history,
        "stage2_history": stage2_history,
    }
    return model, report


def save_gating_bundle(
    *,
    model: MinisterGatingMLP,
    minister_order: Sequence[str],
    feature_names_41: Sequence[str],
    output_model_path: str,
    output_meta_path: str,
    training_report: Dict[str, Any],
    config: GatingTrainingConfig,
    feature_spec: Dict[str, Any] | None = None,
) -> None:
    model_path = Path(output_model_path)
    meta_path = Path(output_meta_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_dim": config.input_dim,
            "hidden_dim": config.hidden_dim,
            "num_ministers": len(minister_order),
            "minister_order": list(minister_order),
            "feature_names_41": list(feature_names_41),
            "feature_spec": feature_spec or {},
        },
        model_path,
    )

    meta = {
        "model_path": str(model_path),
        "minister_order": list(minister_order),
        "feature_names_41": list(feature_names_41),
        "feature_spec": feature_spec or {},
        "config": {
            "input_dim": config.input_dim,
            "hidden_dim": config.hidden_dim,
            "stage1_epochs": config.stage1_epochs,
            "stage2_epochs": config.stage2_epochs,
            "lr": config.lr,
            "weight_decay": config.weight_decay,
            "entropy_reg": config.entropy_reg,
            "prior_reg": config.prior_reg,
            "calibration_brier_weight": config.calibration_brier_weight,
            "regret_weight_alpha": config.regret_weight_alpha,
            "seed": config.seed,
            "early_stop_patience": config.early_stop_patience,
            "prior_weights": list(config.prior_weights) if config.prior_weights else None,
        },
        "training_report": training_report,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_gating_bundle(model_path: str) -> Tuple[MinisterGatingMLP, Dict[str, Any]]:
    payload = torch.load(model_path, map_location="cpu")
    model = MinisterGatingMLP(
        input_dim=int(payload["input_dim"]),
        hidden_dim=int(payload["hidden_dim"]),
        num_ministers=int(payload["num_ministers"]),
    )
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, payload
