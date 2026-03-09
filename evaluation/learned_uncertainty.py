"""
Runtime loader/inference for frozen learned uncertainty predictor artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn


class _UncertaintyMLP(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _feature_value(signals: Dict[str, Any], feature_name: str) -> Optional[float]:
    name = str(feature_name).strip().lower()

    if name in {"entropy", "minister_vote_entropy"}:
        return _to_float_or_none(signals.get("minister_vote_entropy"))
    if name in {"disagreement_entropy"}:
        v = signals.get("disagreement_entropy", signals.get("minister_vote_entropy"))
        return _to_float_or_none(v)
    if name in {"entropy_conditional"}:
        v = signals.get("entropy_conditional", signals.get("minister_vote_entropy"))
        return _to_float_or_none(v)
    if name in {"confidence_variance", "minister_confidence_variance"}:
        return _to_float_or_none(signals.get("minister_confidence_variance"))
    if name in {"margin_uncertainty", "inverse_margin"}:
        margin = _to_float_or_none(signals.get("decision_margin"))
        if margin is None:
            return _to_float_or_none(signals.get("inverse_margin"))
        return float(np.clip(1.0 - margin, 0.0, 1.0))
    if name in {"decision_margin", "margin"}:
        return _to_float_or_none(signals.get("decision_margin"))
    if name in {"embedding_shift"}:
        return _to_float_or_none(signals.get("embedding_shift"))
    if name in {"cluster_error_rate", "cluster_prior"}:
        return _to_float_or_none(signals.get("cluster_error_rate"))
    if name in {"kis_variance"}:
        return _to_float_or_none(signals.get("kis_variance"))
    if name in {"ml_prior_variance"}:
        return _to_float_or_none(signals.get("ml_prior_variance"))
    if name in {"irreversibility_score"}:
        return _to_float_or_none(signals.get("irreversibility_score"))
    if name in {"minister_mean_confidence"}:
        return _to_float_or_none(signals.get("minister_mean_confidence"))
    if name in {"vote_concentration_index"}:
        explicit = _to_float_or_none(signals.get("vote_concentration_index"))
        if explicit is not None:
            return explicit
        ent = _to_float_or_none(signals.get("minister_vote_entropy"))
        if ent is None:
            return None
        return float(np.clip(1.0 - ent, 0.0, 1.0))
    if name in {"confidence"}:
        return _to_float_or_none(signals.get("confidence"))
    return None


class LearnedUncertaintyPredictor:
    def __init__(
        self,
        *,
        model: nn.Module,
        feature_names: List[str],
        medians: np.ndarray,
        means: np.ndarray,
        stds: np.ndarray,
        threshold_1: Optional[float],
        threshold_2: Optional[float],
        threshold_3: Optional[float],
        artifact_path: str,
    ):
        self.model = model.eval()
        self.feature_names = list(feature_names)
        self.medians = medians.astype(float)
        self.means = means.astype(float)
        self.stds = stds.astype(float)
        self.threshold_1 = threshold_1
        self.threshold_2 = threshold_2
        self.threshold_3 = threshold_3
        self.artifact_path = artifact_path

    @classmethod
    def from_json(cls, path: str) -> "LearnedUncertaintyPredictor":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Uncertainty model artifact not found: {p}")
        payload = json.loads(p.read_text(encoding="utf-8"))

        artifact = payload.get("artifact", {}) or {}
        state_dict_raw = artifact.get("state_dict", {}) or {}
        feature_names = artifact.get("feature_names") or payload.get("features") or []
        if not feature_names:
            raise ValueError("Uncertainty model artifact missing feature names.")

        prep = payload.get("preprocessing", {}) or {}
        med = np.asarray(prep.get("imputer_median", []), dtype=float)
        mu = np.asarray(prep.get("standardize_mean", []), dtype=float)
        sd = np.asarray(prep.get("standardize_std", []), dtype=float)
        in_dim = len(feature_names)
        if med.size != in_dim or mu.size != in_dim or sd.size != in_dim:
            raise ValueError(
                f"Preprocessing shape mismatch: expected {in_dim}, got "
                f"median={med.size} mean={mu.size} std={sd.size}"
            )
        sd = np.where(sd < 1e-8, 1.0, sd)

        hidden_dim = int((payload.get("training", {}) or {}).get("hidden_dim", 32))
        model = _UncertaintyMLP(in_dim=in_dim, hidden_dim=hidden_dim)
        state_dict: Dict[str, torch.Tensor] = {}
        for k, v in state_dict_raw.items():
            state_dict[str(k)] = torch.tensor(v, dtype=torch.float32)
        model.load_state_dict(state_dict, strict=True)

        t = payload.get("validation_thresholds", {}) or payload.get("training", {}).get("validation_thresholds", {}) or {}
        threshold_1 = _to_float_or_none(t.get("threshold_1"))
        threshold_2 = _to_float_or_none(t.get("threshold_2"))
        threshold_3 = _to_float_or_none(t.get("threshold_3"))

        return cls(
            model=model,
            feature_names=[str(x) for x in feature_names],
            medians=med,
            means=mu,
            stds=sd,
            threshold_1=threshold_1,
            threshold_2=threshold_2,
            threshold_3=threshold_3,
            artifact_path=str(p),
        )

    def predict(self, signals: Dict[str, Any]) -> float:
        x = np.full((len(self.feature_names),), np.nan, dtype=float)
        for i, name in enumerate(self.feature_names):
            v = _feature_value(signals, name)
            if v is not None:
                x[i] = float(v)
        x = np.where(np.isnan(x), self.medians, x)
        x = (x - self.means) / self.stds
        tensor = torch.from_numpy(x.astype(np.float32, copy=False)).unsqueeze(0)
        with torch.no_grad():
            p = torch.sigmoid(self.model(tensor)).cpu().item()
        return float(np.clip(p, 0.0, 1.0))

    def threshold_config(self) -> Dict[str, Optional[float]]:
        return {
            "threshold_1": self.threshold_1,
            "threshold_2": self.threshold_2,
            "threshold_3": self.threshold_3,
        }

    def metadata(self) -> Dict[str, Any]:
        return {
            "artifact_path": self.artifact_path,
            "feature_names": list(self.feature_names),
            "threshold_1": self.threshold_1,
            "threshold_2": self.threshold_2,
            "threshold_3": self.threshold_3,
        }
