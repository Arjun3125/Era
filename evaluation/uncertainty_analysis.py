#!/usr/bin/env python
"""
Composite uncertainty analysis.

Stage 2:
  U = weighted linear combination of normalized primitives:
      entropy, confidence_variance, inverse_margin, kis_variance (+ optional ml_prior_variance)

Stage 3:
  Empirical validation that higher U predicts higher error probability:
      - correlation(U, error)
      - ROC AUC(U -> error)
      - calibration bins of U vs empirical error rate
      - top-decile error rate

Stage 4:
  Percentile-based control thresholds (T1/T2/T3) exported for policy wiring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import torch
import torch.nn as nn

def _load_split_lookup(path: Path) -> Dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    splits = payload.get("splits", {}) or {}
    lookup: Dict[str, str] = {}
    for split_name, split_payload in splits.items():
        if not isinstance(split_payload, dict):
            continue
        for ids in split_payload.values():
            for sid in ids or []:
                sid_str = str(sid)
                existing = lookup.get(sid_str)
                if existing and existing != str(split_name).lower():
                    raise RuntimeError(
                        f"Scenario '{sid_str}' appears in multiple splits: {existing}, {split_name}"
                    )
                lookup[sid_str] = str(split_name).lower()
    return lookup


def _apply_split_lookup(records: List[Dict[str, Any]], lookup: Dict[str, str]) -> None:
    for rec in records:
        split = str(rec.get("split", "unspecified")).strip().lower()
        if split not in {"", "unspecified", "unknown"}:
            continue
        sid = str(rec.get("scenario_id", ""))
        if sid in lookup:
            rec["split"] = lookup[sid]


def _infer_distribution_from_scenario_id(scenario_id: str) -> str:
    sid = str(scenario_id or "").upper()
    if sid.startswith("ADV_"):
        return "adv"
    if sid.startswith("OOD_"):
        return "ood"
    return "core"


def _normalize_record(record: Dict[str, Any], *, default_run_name: str = "unknown") -> Dict[str, Any]:
    confidence = float(record.get("confidence", record.get("predicted_confidence", 0.0)))
    confidence = float(np.clip(confidence, 0.0, 1.0))
    score_raw = record.get("score")
    if score_raw is None:
        # Fallback when score is not logged: treat binary correctness as coarse score.
        score = float(record.get("correct", record.get("outcome", 0)))
    else:
        score = float(score_raw)
    score = float(np.clip(score, 0.0, 1.0))
    correct = int(record.get("correct", record.get("outcome", 0)))
    sid = str(record.get("scenario_id", ""))
    distribution = str(record.get("distribution", record.get("distribution_type", ""))).strip().lower()
    if not distribution or distribution == "unknown":
        distribution = _infer_distribution_from_scenario_id(sid)
    if distribution == "adversarial":
        distribution = "adv"
    split = str(record.get("split", "unspecified")).strip().lower() or "unspecified"
    uncertainty = record.get("uncertainty", {}) or {}
    return {
        "confidence": confidence,
        "score": score,
        "correct": int(1 if correct else 0),
        "scenario_id": sid,
        "split": split,
        "distribution": distribution,
        "run_name": str(record.get("run_name", default_run_name)),
        "seed": record.get("seed"),
        "uncertainty": {
            "minister_vote_entropy": uncertainty.get("minister_vote_entropy"),
            "minister_confidence_variance": uncertainty.get("minister_confidence_variance"),
            "decision_margin": uncertainty.get("decision_margin"),
            "kis_variance": uncertainty.get("kis_variance"),
            "ml_prior_variance": uncertainty.get("ml_prior_variance"),
            "disagreement_entropy": uncertainty.get("disagreement_entropy"),
            "irreversibility_score": uncertainty.get("irreversibility_score"),
            "minister_mean_confidence": uncertainty.get("minister_mean_confidence"),
            "vote_concentration_index": uncertainty.get("vote_concentration_index"),
        },
    }


def _extract_records_from_run_payload(run_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    run_name = str(run_payload.get("run_name", "unknown"))
    score_lookup: Dict[Tuple[int, str], float] = {}
    by_seed = run_payload.get("scenario_scores_by_seed", {}) or {}
    if isinstance(by_seed, dict):
        for seed_key, sid_map in by_seed.items():
            if not isinstance(sid_map, dict):
                continue
            seed_value = None
            if isinstance(seed_key, str) and seed_key.startswith("seed_"):
                try:
                    seed_value = int(seed_key.split("_", 1)[1])
                except Exception:
                    seed_value = None
            elif isinstance(seed_key, int):
                seed_value = int(seed_key)
            if seed_value is None:
                continue
            for sid, score in sid_map.items():
                try:
                    score_lookup[(int(seed_value), str(sid))] = float(score)
                except Exception:
                    continue

    if isinstance(run_payload.get("confidence_records"), list):
        out: List[Dict[str, Any]] = []
        for row in run_payload["confidence_records"]:
            if not isinstance(row, dict):
                continue
            rec = row
            if rec.get("score") is None:
                sid = str(rec.get("scenario_id", ""))
                seed = rec.get("seed")
                try:
                    seed_i = int(seed)
                except Exception:
                    seed_i = None
                if seed_i is not None:
                    mapped_score = score_lookup.get((seed_i, sid))
                    if mapped_score is not None:
                        rec = dict(rec)
                        rec["score"] = float(mapped_score)
            out.append(_normalize_record(rec, default_run_name=run_name))
        return out
    return []


def _load_records_from_result(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: List[Dict[str, Any]] = []

    if isinstance(payload.get("confidence_records"), list):
        records.extend(_normalize_record(r) for r in payload["confidence_records"])

    if isinstance(payload.get("raw_runs"), dict):
        for run_payload in payload["raw_runs"].values():
            if isinstance(run_payload, dict):
                records.extend(_extract_records_from_run_payload(run_payload))

    if isinstance(payload.get("runs"), dict):
        for run_payload in payload["runs"].values():
            if isinstance(run_payload, dict):
                records.extend(_extract_records_from_run_payload(run_payload))

    if not records:
        records.extend(_extract_records_from_run_payload(payload))
    return records


def load_records(paths: Iterable[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for raw_path in paths:
        p = Path(raw_path)
        if not p.exists():
            raise FileNotFoundError(f"Result JSON not found: {p}")
        records.extend(_load_records_from_result(p))
    return records


def _record_error(record: Dict[str, Any]) -> float:
    score = float(np.clip(float(record.get("score", record.get("correct", 0))), 0.0, 1.0))
    return 1.0 - score


def _default_embedding_dataset_paths() -> List[str]:
    candidates = [
        "evaluation/results/gating_dataset_train_aug6_embed.json",
        "evaluation/results/gating_dataset_val_aug6_embed.json",
        "evaluation/results/gating_dataset_train_aug4_embed.json",
        "evaluation/results/gating_dataset_val_aug4_embed.json",
    ]
    return [p for p in candidates if Path(p).exists()]


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [r for r in payload["rows"] if isinstance(r, dict)]
    return []


def _load_embedding_lookup(
    paths: Iterable[str],
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, Any]]:
    """
    Returns:
      - scenario_id -> embedding vector
      - train_scenario_id -> embedding vector
      - stats dict
    """
    selected_by_sid: Dict[str, Tuple[int, np.ndarray]] = {}
    train_by_sid: Dict[str, np.ndarray] = {}
    dim_hist: Dict[int, int] = {}
    n_rows = 0

    # variant priority: prefer original scenario embedding over augmentation
    variant_priority = {"orig": 0}

    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        for row in _load_rows(path):
            n_rows += 1
            sid = str(row.get("scenario_id", "")).strip()
            vec = row.get("scenario_embedding_raw", None)
            if not sid or not isinstance(vec, list) or not vec:
                continue
            try:
                arr = np.asarray([float(x) for x in vec], dtype=float)
            except Exception:
                continue
            dim = int(arr.size)
            if dim <= 0:
                continue
            dim_hist[dim] = dim_hist.get(dim, 0) + 1
            v_id = str(row.get("variant_id", "")).strip().lower()
            prio = variant_priority.get(v_id, 1)
            prev = selected_by_sid.get(sid)
            if prev is None or prio < prev[0]:
                selected_by_sid[sid] = (prio, arr)
            if str(row.get("split_name", "")).strip().lower() == "train":
                prev_train = train_by_sid.get(sid)
                if prev_train is None or prio < (0 if v_id == "orig" else 1):
                    train_by_sid[sid] = arr

    if not dim_hist:
        return {}, {}, {"n_rows": n_rows, "n_scenarios": 0, "n_train_scenarios": 0, "dim": 0}

    # Keep the most common embedding dimensionality.
    target_dim = max(dim_hist.items(), key=lambda item: item[1])[0]
    scenario_vecs = {
        sid: arr
        for sid, (_, arr) in selected_by_sid.items()
        if int(arr.size) == target_dim
    }
    train_vecs = {
        sid: arr
        for sid, arr in train_by_sid.items()
        if int(arr.size) == target_dim
    }
    return scenario_vecs, train_vecs, {
        "n_rows": n_rows,
        "n_scenarios": int(len(scenario_vecs)),
        "n_train_scenarios": int(len(train_vecs)),
        "dim": int(target_dim),
    }


def _kmeans(
    x: np.ndarray,
    *,
    k: int,
    n_iter: int = 50,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Lightweight k-means for small offline analysis.
    Returns (centroids, labels).
    """
    n = x.shape[0]
    if n == 0:
        return np.zeros((0, x.shape[1] if x.ndim == 2 else 0), dtype=float), np.zeros((0,), dtype=int)
    k_eff = max(1, min(int(k), int(n)))
    rng = np.random.default_rng(seed)
    init_idx = rng.choice(n, size=k_eff, replace=False)
    centroids = x[init_idx].copy()
    labels = np.zeros(n, dtype=int)

    for _ in range(max(1, int(n_iter))):
        # assign
        d2 = ((x[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_labels = np.argmin(d2, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels

        # update
        for c in range(k_eff):
            mask = labels == c
            if not np.any(mask):
                # re-seed empty cluster
                centroids[c] = x[rng.integers(0, n)]
            else:
                centroids[c] = x[mask].mean(axis=0)

    return centroids, labels


def _apply_derived_uncertainty_signals(
    records: List[Dict[str, Any]],
    *,
    scenario_embeddings: Dict[str, np.ndarray],
    train_embeddings: Dict[str, np.ndarray],
    n_entropy_bins: int,
    k_clusters: int,
) -> Dict[str, Any]:
    """
    Adds derived uncertainty fields to each record['uncertainty']:
      - embedding_shift
      - cluster_error_rate
      - entropy_conditional
    """
    if not records:
        return {
            "records_with_embedding": 0,
            "records_with_cluster": 0,
            "records_with_entropy_conditional": 0,
            "cluster_count": 0,
        }

    # ---- embedding shift from training centroid ----
    emb_indices: List[int] = []
    emb_matrix: List[np.ndarray] = []
    for i, rec in enumerate(records):
        sid = str(rec.get("scenario_id", ""))
        vec = scenario_embeddings.get(sid)
        if vec is None:
            continue
        emb_indices.append(i)
        emb_matrix.append(vec)
    records_with_embedding = len(emb_indices)

    distances: Dict[int, float] = {}
    cluster_label_by_index: Dict[int, int] = {}
    if emb_matrix:
        mat = np.vstack(emb_matrix)
        if train_embeddings:
            train_mat = np.vstack(list(train_embeddings.values()))
            centroid = train_mat.mean(axis=0)
        else:
            centroid = mat.mean(axis=0)
        raw_dist = np.sqrt(((mat - centroid[None, :]) ** 2).sum(axis=1))
        dmin = float(np.min(raw_dist))
        dmax = float(np.max(raw_dist))
        span = max(dmax - dmin, 1e-9)
        norm_dist = (raw_dist - dmin) / span
        for idx, val in zip(emb_indices, norm_dist):
            distances[idx] = float(np.clip(val, 0.0, 1.0))

        # ---- cluster_error_rate prior ----
        _, labels = _kmeans(mat, k=k_clusters, n_iter=60, seed=42)
        for idx, c in zip(emb_indices, labels.tolist()):
            cluster_label_by_index[idx] = int(c)

    for i, rec in enumerate(records):
        unc = rec.get("uncertainty", {}) or {}
        unc["embedding_shift"] = distances.get(i)
        rec["uncertainty"] = unc

    # leave-one-out cluster error rates
    cluster_total: Dict[int, int] = {}
    cluster_err: Dict[int, float] = {}
    total_n = 0
    total_err = 0.0
    for i, rec in enumerate(records):
        c = cluster_label_by_index.get(i)
        if c is None:
            continue
        e = _record_error(rec)
        cluster_total[c] = cluster_total.get(c, 0) + 1
        cluster_err[c] = cluster_err.get(c, 0.0) + e
        total_n += 1
        total_err += e

    records_with_cluster = 0
    for i, rec in enumerate(records):
        c = cluster_label_by_index.get(i)
        unc = rec.get("uncertainty", {}) or {}
        if c is None:
            unc["cluster_error_rate"] = None
            rec["uncertainty"] = unc
            continue
        records_with_cluster += 1
        e = _record_error(rec)
        n_c = cluster_total.get(c, 0)
        err_c = cluster_err.get(c, 0.0)
        if n_c > 1:
            loo = (err_c - e) / float(n_c - 1)
        elif total_n > 1:
            loo = (total_err - e) / float(total_n - 1)
        else:
            loo = total_err / max(float(total_n), 1.0)
        unc["cluster_error_rate"] = float(np.clip(loo, 0.0, 1.0))
        rec["uncertainty"] = unc

    # ---- conditional entropy: entropy * historical error-rate-by-entropy-bin (leave-one-out) ----
    entropy_rows: List[Tuple[int, float, float]] = []  # (record_index, entropy, error)
    for i, rec in enumerate(records):
        unc = rec.get("uncertainty", {}) or {}
        e = unc.get("minister_vote_entropy")
        if e is None:
            continue
        entropy_rows.append((i, float(np.clip(float(e), 0.0, 1.0)), _record_error(rec)))

    records_with_entropy_conditional = 0
    if entropy_rows:
        bins = max(2, int(n_entropy_bins))
        edges = np.linspace(0.0, 1.0, bins + 1)
        bin_total = np.zeros(bins, dtype=int)
        bin_err = np.zeros(bins, dtype=float)
        row_bin: Dict[int, int] = {}

        for idx, ent, err in entropy_rows:
            b = int(np.searchsorted(edges, ent, side="right") - 1)
            b = max(0, min(b, bins - 1))
            row_bin[idx] = b
            bin_total[b] += 1
            bin_err[b] += float(err)

        global_err = float(np.mean([err for _, _, err in entropy_rows]))
        for idx, ent, err in entropy_rows:
            b = row_bin[idx]
            n_b = int(bin_total[b])
            err_b = float(bin_err[b])
            if n_b > 1:
                hist_err = (err_b - err) / float(n_b - 1)
            else:
                hist_err = global_err
            cond = float(np.clip(ent * np.clip(hist_err, 0.0, 1.0), 0.0, 1.0))
            unc = records[idx].get("uncertainty", {}) or {}
            unc["entropy_conditional"] = cond
            records[idx]["uncertainty"] = unc
            records_with_entropy_conditional += 1

    return {
        "records_with_embedding": int(records_with_embedding),
        "records_with_cluster": int(records_with_cluster),
        "records_with_entropy_conditional": int(records_with_entropy_conditional),
        "cluster_count": int(len(set(cluster_label_by_index.values()))),
    }


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = rank
        i = j + 1
    return ranks


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    sx = float(np.std(x))
    sy = float(np.std(y))
    if sx == 0.0 or sy == 0.0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    return _pearson(_rankdata(x), _rankdata(y))


def _normalize_component(values: List[float | None]) -> Tuple[List[float], Dict[str, Any]]:
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    if arr.size == 0:
        return [0.0] * len(values), {"present": 0, "min": None, "max": None}
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    if vmax <= vmin:
        out = [0.0 if v is None else 0.0 for v in values]
        return out, {"present": int(arr.size), "min": vmin, "max": vmax}
    out: List[float] = []
    span = vmax - vmin
    for v in values:
        if v is None:
            out.append(0.0)
        else:
            out.append(float(np.clip((float(v) - vmin) / span, 0.0, 1.0)))
    return out, {"present": int(arr.size), "min": vmin, "max": vmax}


def _extract_primitives(records: List[Dict[str, Any]]) -> Dict[str, List[float | None]]:
    entropy: List[float | None] = []
    conf_var: List[float | None] = []
    embedding_shift: List[float | None] = []
    cluster_error_rate: List[float | None] = []
    kis_var: List[float | None] = []
    ml_prior_var: List[float | None] = []
    inv_margin: List[float | None] = []
    for rec in records:
        unc = rec.get("uncertainty", {}) or {}
        e = unc.get("entropy_conditional", unc.get("minister_vote_entropy"))
        cv = unc.get("minister_confidence_variance")
        es = unc.get("embedding_shift")
        cer = unc.get("cluster_error_rate")
        kv = unc.get("kis_variance")
        mpv = unc.get("ml_prior_variance")
        margin = unc.get("decision_margin")
        entropy.append(None if e is None else float(e))
        conf_var.append(None if cv is None else float(cv))
        embedding_shift.append(None if es is None else float(es))
        cluster_error_rate.append(None if cer is None else float(cer))
        kis_var.append(None if kv is None else float(kv))
        ml_prior_var.append(None if mpv is None else float(mpv))
        if margin is None:
            inv_margin.append(None)
        else:
            inv_margin.append(float(np.clip(1.0 - float(margin), 0.0, 1.0)))
    return {
        "entropy": entropy,
        "confidence_variance": conf_var,
        "embedding_shift": embedding_shift,
        "cluster_error_rate": cluster_error_rate,
        "kis_variance": kis_var,
        "ml_prior_variance": ml_prior_var,
        "inverse_margin": inv_margin,
    }


def _compute_u(
    records: List[Dict[str, Any]],
    *,
    w_entropy: float,
    w_conf_var: float,
    w_embedding_shift: float,
    w_cluster_error_rate: float,
    w_kis_var: float,
    w_inverse_margin: float,
    w_ml_prior_var: float,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    primitives = _extract_primitives(records)
    entropy_n, entropy_stats = _normalize_component(primitives["entropy"])
    conf_n, conf_stats = _normalize_component(primitives["confidence_variance"])
    emb_shift_n, emb_shift_stats = _normalize_component(primitives["embedding_shift"])
    cluster_err_n, cluster_err_stats = _normalize_component(primitives["cluster_error_rate"])
    kis_n, kis_stats = _normalize_component(primitives["kis_variance"])
    ml_prior_n, ml_prior_stats = _normalize_component(primitives["ml_prior_variance"])
    inv_margin_n, inv_margin_stats = _normalize_component(primitives["inverse_margin"])

    n_with_signal = 0
    u_values: List[float] = []
    effective_weight_sums: List[float] = []
    for i in range(len(records)):
        weighted_sum = 0.0
        weight_sum = 0.0
        if primitives["entropy"][i] is not None:
            weighted_sum += w_entropy * entropy_n[i]
            weight_sum += w_entropy
        if primitives["confidence_variance"][i] is not None:
            weighted_sum += w_conf_var * conf_n[i]
            weight_sum += w_conf_var
        if primitives["embedding_shift"][i] is not None and w_embedding_shift > 0.0:
            weighted_sum += w_embedding_shift * emb_shift_n[i]
            weight_sum += w_embedding_shift
        if primitives["cluster_error_rate"][i] is not None and w_cluster_error_rate > 0.0:
            weighted_sum += w_cluster_error_rate * cluster_err_n[i]
            weight_sum += w_cluster_error_rate
        if primitives["kis_variance"][i] is not None:
            weighted_sum += w_kis_var * kis_n[i]
            weight_sum += w_kis_var
        if primitives["ml_prior_variance"][i] is not None and w_ml_prior_var > 0.0:
            weighted_sum += w_ml_prior_var * ml_prior_n[i]
            weight_sum += w_ml_prior_var
        if primitives["inverse_margin"][i] is not None:
            weighted_sum += w_inverse_margin * inv_margin_n[i]
            weight_sum += w_inverse_margin

        if any(
            x is not None
            for x in (
                primitives["entropy"][i],
                primitives["confidence_variance"][i],
                primitives["embedding_shift"][i],
                primitives["cluster_error_rate"][i],
                primitives["kis_variance"][i],
                primitives["ml_prior_variance"][i],
                primitives["inverse_margin"][i],
            )
        ):
            n_with_signal += 1
        effective_weight_sums.append(float(weight_sum))
        if weight_sum <= 1e-9:
            u_values.append(0.0)
        else:
            u_values.append(float(np.clip(weighted_sum / weight_sum, 0.0, 1.0)))

    u = np.asarray(u_values, dtype=float)

    details = {
        "weights": {
            "entropy": float(w_entropy),
            "confidence_variance": float(w_conf_var),
            "embedding_shift": float(w_embedding_shift),
            "cluster_error_rate": float(w_cluster_error_rate),
            "kis_variance": float(w_kis_var),
            "ml_prior_variance": float(w_ml_prior_var),
            "inverse_margin": float(w_inverse_margin),
        },
        "component_stats": {
            "entropy": entropy_stats,
            "confidence_variance": conf_stats,
            "embedding_shift": emb_shift_stats,
            "cluster_error_rate": cluster_err_stats,
            "kis_variance": kis_stats,
            "ml_prior_variance": ml_prior_stats,
            "inverse_margin": inv_margin_stats,
        },
        "records_with_any_primitive_signal": int(n_with_signal),
        "records_total": int(len(records)),
        "effective_weight_sum_mean": float(np.mean(effective_weight_sums)) if effective_weight_sums else 0.0,
        "effective_weight_sum_min": float(np.min(effective_weight_sums)) if effective_weight_sums else 0.0,
        "effective_weight_sum_max": float(np.max(effective_weight_sums)) if effective_weight_sums else 0.0,
    }
    return u, details


def _compute_high_error_labels(
    scores: np.ndarray,
    *,
    mode: str,
    threshold: float,
    quantile: float,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    mode_l = str(mode).strip().lower()
    if mode_l == "quantile":
        q = float(np.clip(quantile, 0.01, 0.99))
        k = max(1, int(np.ceil(q * len(scores))))
        order = np.argsort(scores, kind="stable")
        high_error = np.zeros(len(scores), dtype=float)
        high_error[order[:k]] = 1.0
        thr = float(scores[order[k - 1]])
        return high_error, {
            "mode": "quantile",
            "quantile": q,
            "selection": "bottom_rank_quantile",
            "score_threshold": thr,
            "selected_count": int(k),
        }
    thr = float(np.clip(threshold, 0.0, 1.0))
    high_error = (scores < thr).astype(float)
    return high_error, {"mode": "threshold", "score_threshold": thr}


def _feature_value(record: Dict[str, Any], feature_name: str) -> float | None:
    unc = record.get("uncertainty", {}) or {}
    name = str(feature_name).strip().lower()
    if name in {"entropy", "minister_vote_entropy"}:
        return unc.get("minister_vote_entropy")
    if name in {"disagreement_entropy"}:
        return unc.get("disagreement_entropy", unc.get("minister_vote_entropy"))
    if name in {"entropy_conditional"}:
        return unc.get("entropy_conditional", unc.get("minister_vote_entropy"))
    if name in {"confidence_variance", "minister_confidence_variance"}:
        return unc.get("minister_confidence_variance")
    if name in {"margin_uncertainty", "inverse_margin"}:
        margin = unc.get("decision_margin")
        if margin is None:
            return None
        return float(np.clip(1.0 - float(margin), 0.0, 1.0))
    if name in {"decision_margin", "margin"}:
        return unc.get("decision_margin")
    if name in {"embedding_shift"}:
        return unc.get("embedding_shift")
    if name in {"cluster_error_rate", "cluster_prior"}:
        return unc.get("cluster_error_rate")
    if name in {"kis_variance"}:
        return unc.get("kis_variance")
    if name in {"ml_prior_variance"}:
        return unc.get("ml_prior_variance")
    if name in {"irreversibility_score"}:
        return unc.get("irreversibility_score")
    if name in {"minister_mean_confidence"}:
        return unc.get("minister_mean_confidence")
    if name in {"vote_concentration_index"}:
        explicit = unc.get("vote_concentration_index")
        if explicit is not None:
            return explicit
        ent = unc.get("minister_vote_entropy")
        if ent is None:
            return None
        return float(np.clip(1.0 - float(ent), 0.0, 1.0))
    if name in {"confidence"}:
        return record.get("confidence")
    return None


def _build_feature_matrix(
    records: List[Dict[str, Any]],
    feature_names: List[str],
) -> Tuple[np.ndarray, List[str]]:
    x = np.full((len(records), len(feature_names)), np.nan, dtype=float)
    for i, rec in enumerate(records):
        for j, name in enumerate(feature_names):
            v = _feature_value(rec, name)
            if v is None:
                continue
            x[i, j] = float(v)
    return x, feature_names


def _split_indices(
    records: List[Dict[str, Any]],
    *,
    seed: int,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    split_vals = [str(r.get("split", "unspecified")).strip().lower() for r in records]
    train_idx = np.asarray([i for i, s in enumerate(split_vals) if s == "train"], dtype=int)
    val_idx = np.asarray([i for i, s in enumerate(split_vals) if s in {"val", "validation"}], dtype=int)
    test_idx = np.asarray([i for i, s in enumerate(split_vals) if s == "test"], dtype=int)
    if train_idx.size > 0 and (val_idx.size > 0 or test_idx.size > 0):
        if val_idx.size == 0:
            val_idx = test_idx.copy()
        if test_idx.size == 0:
            test_idx = val_idx.copy()
        return train_idx, val_idx, test_idx, {"strategy": "explicit_split_labels"}

    # Fallback: scenario-level deterministic split to limit leakage.
    by_sid: Dict[str, List[int]] = {}
    for i, rec in enumerate(records):
        sid = str(rec.get("scenario_id", f"row_{i}"))
        by_sid.setdefault(sid, []).append(i)
    sids = sorted(by_sid.keys())
    rng = np.random.default_rng(seed)
    rng.shuffle(sids)
    n = len(sids)
    n_train = max(1, int(round(train_ratio * n)))
    n_val = max(1, int(round(val_ratio * n)))
    n_test = max(1, n - n_train - n_val)
    if n_train + n_val + n_test > n:
        n_test = max(1, n - n_train - n_val)
    train_sids = set(sids[:n_train])
    val_sids = set(sids[n_train : n_train + n_val])
    test_sids = set(sids[n_train + n_val : n_train + n_val + n_test])
    if not test_sids:
        test_sids = val_sids.copy()
    train_i, val_i, test_i = [], [], []
    for sid, idxs in by_sid.items():
        if sid in train_sids:
            train_i.extend(idxs)
        elif sid in val_sids:
            val_i.extend(idxs)
        elif sid in test_sids:
            test_i.extend(idxs)
    return (
        np.asarray(sorted(train_i), dtype=int),
        np.asarray(sorted(val_i), dtype=int),
        np.asarray(sorted(test_i), dtype=int),
        {
            "strategy": "scenario_id_random_split",
            "seed": int(seed),
            "n_scenarios": int(n),
            "n_train_scenarios": int(len(train_sids)),
            "n_val_scenarios": int(len(val_sids)),
            "n_test_scenarios": int(len(test_sids)),
        },
    )


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


def _binary_metrics(y_true: np.ndarray, scores: np.ndarray) -> Dict[str, Any]:
    y = y_true.astype(float)
    s = scores.astype(float)
    auc = _roc_auc_from_scores(y.astype(int), s)
    rho = _spearman(s, y)
    overall = float(np.mean(y)) if y.size else 0.0
    if s.size == 0:
        return {
            "n": 0,
            "auc": None,
            "spearman": 0.0,
            "overall_rate": None,
            "top10_rate": None,
            "top10_ratio": None,
        }
    q90 = float(np.quantile(s, 0.90))
    top10 = s >= q90
    top10_rate = float(np.mean(y[top10])) if np.any(top10) else None
    top10_ratio = (
        float(top10_rate / overall)
        if top10_rate is not None and overall > 0.0
        else None
    )
    return {
        "n": int(len(y)),
        "auc": auc,
        "spearman": float(rho),
        "overall_rate": overall,
        "top10_rate": top10_rate,
        "top10_ratio": top10_ratio,
    }


def _train_learned_uncertainty_predictor(
    records: List[Dict[str, Any]],
    *,
    feature_names: List[str],
    high_error_mode: str,
    high_error_threshold: float,
    high_error_quantile: float,
    hidden_dim: int,
    epochs: int,
    lr: float,
    weight_decay: float,
    seed: int,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    if not records:
        return np.asarray([], dtype=float), {"status": "no_records"}

    scores = np.asarray(
        [float(np.clip(float(r.get("score", r.get("correct", 0))), 0.0, 1.0)) for r in records],
        dtype=float,
    )
    y, high_error_def = _compute_high_error_labels(
        scores,
        mode=high_error_mode,
        threshold=high_error_threshold,
        quantile=high_error_quantile,
    )
    x_raw, feat_names = _build_feature_matrix(records, feature_names)
    if x_raw.shape[1] == 0:
        raise RuntimeError("No learned uncertainty features configured.")

    train_idx, val_idx, test_idx, split_info = _split_indices(records, seed=seed)
    if train_idx.size == 0:
        raise RuntimeError("No training rows available for learned uncertainty predictor.")

    train_x = x_raw[train_idx]
    medians_list: List[float] = []
    for j in range(train_x.shape[1]):
        col = train_x[:, j]
        valid = col[~np.isnan(col)]
        if valid.size == 0:
            medians_list.append(0.0)
        else:
            medians_list.append(float(np.median(valid)))
    medians = np.asarray(medians_list, dtype=float)
    x_imp = np.where(np.isnan(x_raw), medians[None, :], x_raw)

    mu = x_imp[train_idx].mean(axis=0)
    sigma = x_imp[train_idx].std(axis=0)
    sigma = np.where(sigma < 1e-8, 1.0, sigma)
    x_std = (x_imp - mu[None, :]) / sigma[None, :]

    torch.manual_seed(seed)
    np.random.seed(seed)
    model = _UncertaintyMLP(in_dim=x_std.shape[1], hidden_dim=max(4, int(hidden_dim)))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.BCEWithLogitsLoss()

    x_t = torch.tensor(x_std, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32)
    train_t = torch.tensor(train_idx, dtype=torch.long)
    val_t = torch.tensor(val_idx, dtype=torch.long)

    best_state: Dict[str, torch.Tensor] | None = None
    best_auc = -1.0
    patience = 30
    stale = 0

    for _ in range(max(1, int(epochs))):
        model.train()
        optimizer.zero_grad()
        logits = model(x_t[train_t])
        loss = criterion(logits, y_t[train_t])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(x_t[val_t]) if val_idx.size > 0 else model(x_t[train_t])
            val_probs = torch.sigmoid(val_logits).detach().cpu().numpy()
        val_labels = y[val_idx] if val_idx.size > 0 else y[train_idx]
        val_auc = _roc_auc_from_scores(val_labels.astype(int), val_probs)
        score = float(val_auc) if val_auc is not None else 0.0
        if score > best_auc:
            best_auc = score
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(x_t)).detach().cpu().numpy().astype(float)

    train_metrics = _binary_metrics(y[train_idx], probs[train_idx])
    val_metrics = _binary_metrics(y[val_idx], probs[val_idx]) if val_idx.size > 0 else {"n": 0}
    test_metrics = _binary_metrics(y[test_idx], probs[test_idx]) if test_idx.size > 0 else {"n": 0}
    all_metrics = _binary_metrics(y, probs)
    val_source_idx = val_idx if val_idx.size > 0 else train_idx
    val_probs_for_thresholds = probs[val_source_idx]
    t1 = float(np.quantile(val_probs_for_thresholds, 0.90))
    t2 = float(np.quantile(val_probs_for_thresholds, 0.75))

    details = {
        "mode": "learned_mlp",
        "features": feat_names,
        "high_error_definition": high_error_def,
        "training": {
            "hidden_dim": int(hidden_dim),
            "epochs": int(epochs),
            "learning_rate": float(lr),
            "weight_decay": float(weight_decay),
            "split_info": split_info,
            "n_train": int(train_idx.size),
            "n_val": int(val_idx.size),
            "n_test": int(test_idx.size),
        },
        "validation_thresholds": {
            "source": "val" if val_idx.size > 0 else "train_fallback",
            "threshold_1": t1,
            "threshold_2": t2,
            "threshold_3": t2,
        },
        "metrics": {
            "train": train_metrics,
            "val": val_metrics,
            "test": test_metrics,
            "all": all_metrics,
        },
        "preprocessing": {
            "imputer_median": medians.tolist(),
            "standardize_mean": mu.tolist(),
            "standardize_std": sigma.tolist(),
        },
        "frozen_artifact": {
            "state_dict": {k: v.detach().cpu().numpy().tolist() for k, v in model.state_dict().items()},
            "feature_names": feat_names,
        },
    }
    return probs, details


def _bucket_metrics(u: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> List[Dict[str, Any]]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows: List[Dict[str, Any]] = []
    for i in range(n_bins):
        lo = float(edges[i])
        hi = float(edges[i + 1])
        if i == n_bins - 1:
            mask = (u >= lo) & (u <= hi)
        else:
            mask = (u >= lo) & (u < hi)
        n = int(np.sum(mask))
        if n == 0:
            rows.append(
                {
                    "bin": i,
                    "range": [lo, hi],
                    "n": 0,
                    "mean_u": None,
                    "accuracy": None,
                    "error_rate": None,
                }
            )
            continue
        acc = float(np.mean(correct[mask]))
        rows.append(
            {
                "bin": i,
                "range": [lo, hi],
                "n": n,
                "mean_u": float(np.mean(u[mask])),
                "accuracy": acc,
                "error_rate": float(1.0 - acc),
            }
        )
    return rows


def _roc_auc_from_scores(labels: np.ndarray, scores: np.ndarray) -> float | None:
    """
    Rank-based ROC AUC without sklearn dependency.
    labels: 0/1 (1 = positive class)
    scores: higher score -> more likely positive class
    """
    if len(labels) == 0:
        return None
    labels = labels.astype(int)
    n_pos = int(np.sum(labels == 1))
    n_neg = int(np.sum(labels == 0))
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = _rankdata(scores.astype(float))
    sum_pos_ranks = float(np.sum(ranks[labels == 1]))
    auc = (sum_pos_ranks - (n_pos * (n_pos + 1) / 2.0)) / float(n_pos * n_neg)
    return float(np.clip(auc, 0.0, 1.0))


def _auc_quality_label(auc: float | None) -> str:
    if auc is None:
        return "UNDEFINED"
    if auc >= 0.7:
        return "STRONG"
    if auc >= 0.6:
        return "USABLE"
    return "WEAK"


def _validate(
    records: List[Dict[str, Any]],
    u: np.ndarray,
    *,
    n_bins: int = 10,
    high_error_mode: str = "threshold",
    high_error_threshold: float = 0.6,
    high_error_quantile: float = 0.3,
) -> Dict[str, Any]:
    if len(records) == 0:
        return {
            "n": 0,
            "mean_score": None,
            "mean_continuous_error": None,
            "high_error_definition": None,
            "high_error_rate": None,
            "overall_error_rate": None,
            "pearson_u_error": 0.0,
            "spearman_u_error": 0.0,
            "pearson_u_accuracy": 0.0,
            "roc_auc_u_predicts_error": None,
            "auc_quality": "UNDEFINED",
            "low_u_accuracy": None,
            "high_u_accuracy": None,
            "accuracy_drop_high_minus_low": None,
            "top_decile_threshold_u": None,
            "top_decile_n": 0,
            "top_decile_error_rate": None,
            "top_decile_error_concentration_ratio": None,
            "top_quintile_threshold_u": None,
            "top_quintile_n": 0,
            "top_quintile_error_rate": None,
            "top_quintile_error_concentration_ratio": None,
            "supports_higher_u_lower_accuracy": False,
            "bins": [],
        }

    scores = np.asarray(
        [float(np.clip(float(r.get("score", r.get("correct", 0))), 0.0, 1.0)) for r in records],
        dtype=float,
    )
    continuous_error = 1.0 - scores

    high_error, high_error_def = _compute_high_error_labels(
        scores,
        mode=high_error_mode,
        threshold=high_error_threshold,
        quantile=high_error_quantile,
    )

    high_error_rate = float(np.mean(high_error))
    overall_error_rate = high_error_rate
    pearson_u_error = _pearson(u, continuous_error)
    spearman_u_error = _spearman(u, continuous_error)
    pearson_u_accuracy = _pearson(u, scores)
    auc = _roc_auc_from_scores(high_error.astype(int), u)

    q25 = float(np.quantile(u, 0.25))
    q75 = float(np.quantile(u, 0.75))
    q90 = float(np.quantile(u, 0.90))
    q80 = float(np.quantile(u, 0.80))
    low_mask = u <= q25
    high_mask = u >= q75
    top_decile_mask = u >= q90
    top_quintile_mask = u >= q80
    low_acc = float(np.mean(scores[low_mask])) if np.any(low_mask) else None
    high_acc = float(np.mean(scores[high_mask])) if np.any(high_mask) else None
    top_decile_error = float(np.mean(high_error[top_decile_mask])) if np.any(top_decile_mask) else None
    top_quintile_error = float(np.mean(high_error[top_quintile_mask])) if np.any(top_quintile_mask) else None
    top_decile_ratio = (
        float(top_decile_error / overall_error_rate)
        if top_decile_error is not None and overall_error_rate > 0.0
        else None
    )
    top_quintile_ratio = (
        float(top_quintile_error / overall_error_rate)
        if top_quintile_error is not None and overall_error_rate > 0.0
        else None
    )
    acc_drop = None
    if low_acc is not None and high_acc is not None:
        acc_drop = float(low_acc - high_acc)

    supports = bool(
        pearson_u_error > 0.0
        and spearman_u_error > 0.0
        and pearson_u_accuracy < 0.0
        and (acc_drop is not None and acc_drop > 0.0)
    )

    return {
        "n": int(len(records)),
        "mean_score": float(np.mean(scores)),
        "mean_continuous_error": float(np.mean(continuous_error)),
        "high_error_definition": high_error_def,
        "high_error_rate": high_error_rate,
        "overall_error_rate": overall_error_rate,
        "pearson_u_error": float(pearson_u_error),
        "spearman_u_error": float(spearman_u_error),
        "pearson_u_accuracy": float(pearson_u_accuracy),
        "roc_auc_u_predicts_error": auc,
        "auc_quality": _auc_quality_label(auc),
        "low_u_accuracy": low_acc,
        "high_u_accuracy": high_acc,
        "accuracy_drop_high_minus_low": acc_drop,
        "top_decile_threshold_u": q90,
        "top_decile_n": int(np.sum(top_decile_mask)),
        "top_decile_error_rate": top_decile_error,
        "top_decile_error_concentration_ratio": top_decile_ratio,
        "top_quintile_threshold_u": q80,
        "top_quintile_n": int(np.sum(top_quintile_mask)),
        "top_quintile_error_rate": top_quintile_error,
        "top_quintile_error_concentration_ratio": top_quintile_ratio,
        "supports_higher_u_lower_accuracy": supports,
        "bins": _bucket_metrics(u, scores, n_bins=n_bins),
    }


def _subset(records: List[Dict[str, Any]], *, distribution: str | None = None) -> List[Dict[str, Any]]:
    if distribution is None:
        return records
    d = distribution.lower()
    return [r for r in records if str(r.get("distribution", "")).lower() == d]


def _has_any_uncertainty_signal(record: Dict[str, Any]) -> bool:
    unc = record.get("uncertainty", {}) or {}
    return any(
        unc.get(key) is not None
        for key in (
            "entropy_conditional",
            "minister_vote_entropy",
            "minister_confidence_variance",
            "decision_margin",
            "embedding_shift",
            "cluster_error_rate",
            "kis_variance",
            "ml_prior_variance",
            "irreversibility_score",
            "disagreement_entropy",
            "minister_mean_confidence",
            "vote_concentration_index",
        )
    )


def _control_thresholds(u: np.ndarray) -> Dict[str, float | int | None]:
    if u.size == 0:
        return {
            "n": 0,
            "threshold_1": None,  # DARBAR trigger
            "threshold_2": None,  # depth escalation band lower bound
            "threshold_3": None,  # optional low-certainty threshold
        }
    t1 = float(np.quantile(u, 0.90))
    t2 = float(np.quantile(u, 0.75))
    return {
        "n": int(u.size),
        "threshold_1": t1,
        "threshold_2": t2,
        # Keep threshold_3 aligned to the caution band lower bound by default.
        "threshold_3": t2,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Composite uncertainty analysis")
    parser.add_argument("--inputs", nargs="+", required=True, help="Result JSON paths with confidence records.")
    parser.add_argument("--split-manifest", default=None, help="Optional split manifest to backfill split labels.")
    parser.add_argument("--include-run-names", default=None, help="Optional comma-separated run_name allowlist.")
    parser.add_argument("--output-json", default="evaluation/results/uncertainty_analysis.json")
    parser.add_argument(
        "--output-enriched-records-json",
        default=None,
        help="Optional path to save per-decision rows with derived uncertainty signals and U.",
    )
    parser.add_argument(
        "--embedding-datasets",
        nargs="*",
        default=None,
        help=(
            "Optional embedding dataset JSON paths (from build_phase2_gating_dataset). "
            "If omitted, auto-discovers common *_embed files."
        ),
    )
    parser.add_argument("--k-clusters", type=int, default=8, help="KMeans cluster count for cluster_error_rate prior.")
    parser.add_argument("--entropy-bins", type=int, default=10, help="Entropy bins for conditional entropy prior.")
    parser.add_argument("--n-bins", type=int, default=10)
    parser.add_argument(
        "--high-error-mode",
        choices=["threshold", "quantile"],
        default="threshold",
        help="How to define binary high-severity error label used for AUC/concentration.",
    )
    parser.add_argument(
        "--high-error-threshold",
        type=float,
        default=0.6,
        help="Score threshold for high_error when --high-error-mode threshold.",
    )
    parser.add_argument(
        "--high-error-quantile",
        type=float,
        default=0.3,
        help="Bottom score quantile for high_error when --high-error-mode quantile.",
    )
    parser.add_argument(
        "--u-mode",
        choices=["manual", "learned"],
        default="manual",
        help="manual=weighted linear U, learned=shallow MLP uncertainty predictor.",
    )
    parser.add_argument(
        "--learned-feature-names",
        default=(
            "entropy_conditional,margin_uncertainty,confidence_variance,embedding_shift,"
            "cluster_error_rate,kis_variance,ml_prior_variance,irreversibility_score,"
            "disagreement_entropy,minister_mean_confidence,vote_concentration_index,confidence"
        ),
        help="Comma-separated feature names used when --u-mode learned.",
    )
    parser.add_argument("--learned-hidden-dim", type=int, default=32)
    parser.add_argument("--learned-epochs", type=int, default=250)
    parser.add_argument("--learned-lr", type=float, default=1e-3)
    parser.add_argument("--learned-weight-decay", type=float, default=1e-4)
    parser.add_argument("--learned-seed", type=int, default=42)
    parser.add_argument(
        "--learned-model-output",
        default=None,
        help="Optional artifact output path for learned uncertainty model (JSON).",
    )
    parser.add_argument("--w-entropy", type=float, default=0.1)
    parser.add_argument("--w-confidence-variance", type=float, default=0.2)
    parser.add_argument("--w-embedding-shift", type=float, default=0.2)
    parser.add_argument("--w-cluster-error-rate", type=float, default=0.2)
    parser.add_argument("--w-kis-variance", type=float, default=0.1)
    parser.add_argument("--w-inverse-margin", type=float, default=0.3)
    parser.add_argument("--w-ml-prior-variance", type=float, default=0.0)
    args = parser.parse_args()

    records = load_records(args.inputs)
    if args.split_manifest:
        lookup = _load_split_lookup(Path(args.split_manifest))
        _apply_split_lookup(records, lookup)

    if args.include_run_names:
        allow = {x.strip() for x in args.include_run_names.split(",") if x.strip()}
        records = [r for r in records if r.get("run_name") in allow]
    if not records:
        raise RuntimeError("No records available for uncertainty analysis.")

    embedding_paths = (
        [str(p) for p in (args.embedding_datasets or [])]
        if args.embedding_datasets is not None
        else _default_embedding_dataset_paths()
    )
    scenario_embeddings, train_embeddings, embedding_stats = _load_embedding_lookup(embedding_paths)
    derived_stats = _apply_derived_uncertainty_signals(
        records,
        scenario_embeddings=scenario_embeddings,
        train_embeddings=train_embeddings,
        n_entropy_bins=max(2, int(args.entropy_bins)),
        k_clusters=max(2, int(args.k_clusters)),
    )

    learned_features = [
        x.strip() for x in str(args.learned_feature_names).split(",") if x.strip()
    ]
    if args.u_mode == "learned":
        u, details = _train_learned_uncertainty_predictor(
            records,
            feature_names=learned_features,
            high_error_mode=args.high_error_mode,
            high_error_threshold=args.high_error_threshold,
            high_error_quantile=args.high_error_quantile,
            hidden_dim=args.learned_hidden_dim,
            epochs=args.learned_epochs,
            lr=args.learned_lr,
            weight_decay=args.learned_weight_decay,
            seed=args.learned_seed,
        )
    else:
        u, details = _compute_u(
            records,
            w_entropy=args.w_entropy,
            w_conf_var=args.w_confidence_variance,
            w_embedding_shift=args.w_embedding_shift,
            w_cluster_error_rate=args.w_cluster_error_rate,
            w_kis_var=args.w_kis_variance,
            w_inverse_margin=args.w_inverse_margin,
            w_ml_prior_var=args.w_ml_prior_variance,
        )

    dist_arr = np.asarray(
        [str(r.get("distribution", "")).lower() for r in records],
        dtype=object,
    )
    mask_core = np.asarray([d == "core" for d in dist_arr], dtype=bool)
    mask_ood = np.asarray([d == "ood" for d in dist_arr], dtype=bool)
    mask_adv = np.asarray([d == "adv" for d in dist_arr], dtype=bool)
    signal_mask = np.asarray([_has_any_uncertainty_signal(r) for r in records], dtype=bool)
    signal_core_mask = mask_core & signal_mask
    signal_ood_mask = mask_ood & signal_mask
    signal_adv_mask = mask_adv & signal_mask

    validation_all = _validate(
        records,
        u,
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_core = _validate(
        _subset(records, distribution="core"),
        u[mask_core],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_ood = _validate(
        _subset(records, distribution="ood"),
        u[mask_ood],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_adv = _validate(
        _subset(records, distribution="adv"),
        u[mask_adv],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_signal_all = _validate(
        [records[i] for i, keep in enumerate(signal_mask) if keep],
        u[signal_mask],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_signal_core = _validate(
        [records[i] for i, keep in enumerate(signal_core_mask) if keep],
        u[signal_core_mask],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_signal_ood = _validate(
        [records[i] for i, keep in enumerate(signal_ood_mask) if keep],
        u[signal_ood_mask],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )
    validation_signal_adv = _validate(
        [records[i] for i, keep in enumerate(signal_adv_mask) if keep],
        u[signal_adv_mask],
        n_bins=args.n_bins,
        high_error_mode=args.high_error_mode,
        high_error_threshold=args.high_error_threshold,
        high_error_quantile=args.high_error_quantile,
    )

    if args.u_mode == "learned" and args.learned_model_output:
        artifact = (details.get("frozen_artifact", {}) or {})
        artifact_payload = {
            "u_mode": "learned",
            "model_type": "shallow_mlp",
            "high_error_mode": str(args.high_error_mode),
            "high_error_threshold": float(args.high_error_threshold),
            "high_error_quantile": float(args.high_error_quantile),
            "artifact": artifact,
            "training": details.get("training", {}),
            "validation_thresholds": details.get("validation_thresholds", {}),
            "features": details.get("features", []),
            "preprocessing": details.get("preprocessing", {}),
        }
        model_out = Path(args.learned_model_output)
        model_out.parent.mkdir(parents=True, exist_ok=True)
        model_out.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")
        details["artifact_output_path"] = str(model_out)
        # Keep the main analysis JSON compact.
        details.pop("frozen_artifact", None)

    if args.u_mode == "learned":
        thresholds_all_mask = np.ones(len(u), dtype=bool)
        thresholds_core_mask = mask_core
        thresholds_ood_mask = mask_ood
        thresholds_adv_mask = mask_adv
        u_formula = "U = learned MLP probability of high_error"
        u_norm = "train-split median imputation + z-score standardization"
    else:
        thresholds_all_mask = signal_mask
        thresholds_core_mask = signal_core_mask
        thresholds_ood_mask = signal_ood_mask
        thresholds_adv_mask = signal_adv_mask
        u_formula = (
            "U = weighted_mean(margin_uncertainty, confidence_variance, embedding_shift, "
            "cluster_error_rate, entropy_conditional, kis_variance, ml_prior_variance) "
            "over available components"
        )
        u_norm = "min-max to [0,1] per component on analysis set"

    out: Dict[str, Any] = {
        "metadata": {
            "n_records": int(len(records)),
            "inputs": list(args.inputs),
            "embedding_datasets": embedding_paths,
            "n_bins": int(args.n_bins),
            "k_clusters": int(args.k_clusters),
            "entropy_bins": int(args.entropy_bins),
            "high_error_mode": str(args.high_error_mode),
            "high_error_threshold": float(args.high_error_threshold),
            "high_error_quantile": float(args.high_error_quantile),
            "u_mode": str(args.u_mode),
            "learned_feature_names": learned_features,
        },
        "composite_definition": {
            "formula": u_formula,
            "normalization": u_norm,
            "embedding_source": embedding_stats,
            "derived_signal_stats": derived_stats,
            **details,
        },
        "validation": {
            "all": validation_all,
            "core": validation_core,
            "ood": validation_ood,
            "adv": validation_adv,
            "with_signal": {
                "all": validation_signal_all,
                "core": validation_signal_core,
                "ood": validation_signal_ood,
                "adv": validation_signal_adv,
            },
        },
        "control_thresholds": {
            "all": _control_thresholds(u[thresholds_all_mask]),
            "core": _control_thresholds(u[thresholds_core_mask]),
            "ood": _control_thresholds(u[thresholds_ood_mask]),
            "adv": _control_thresholds(u[thresholds_adv_mask]),
        },
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    if args.output_enriched_records_json:
        enriched_rows: List[Dict[str, Any]] = []
        for i, rec in enumerate(records):
            unc = rec.get("uncertainty", {}) or {}
            enriched_rows.append(
                {
                    "scenario_id": str(rec.get("scenario_id", "")),
                    "run_name": str(rec.get("run_name", "")),
                    "distribution": str(rec.get("distribution", "")),
                    "split": str(rec.get("split", "")),
                    "seed": rec.get("seed"),
                    "correct": int(rec.get("correct", 0)),
                    "score": float(np.clip(float(rec.get("score", rec.get("correct", 0))), 0.0, 1.0)),
                    "error_continuous": float(
                        1.0 - float(np.clip(float(rec.get("score", rec.get("correct", 0))), 0.0, 1.0))
                    ),
                    "error": float(1 - int(rec.get("correct", 0))),
                    "u": float(u[i]),
                    "uncertainty": {
                        "minister_vote_entropy": unc.get("minister_vote_entropy"),
                        "disagreement_entropy": unc.get("disagreement_entropy"),
                        "entropy_conditional": unc.get("entropy_conditional"),
                        "minister_confidence_variance": unc.get("minister_confidence_variance"),
                        "minister_mean_confidence": unc.get("minister_mean_confidence"),
                        "vote_concentration_index": unc.get("vote_concentration_index"),
                        "irreversibility_score": unc.get("irreversibility_score"),
                        "decision_margin": unc.get("decision_margin"),
                        "embedding_shift": unc.get("embedding_shift"),
                        "cluster_error_rate": unc.get("cluster_error_rate"),
                        "kis_variance": unc.get("kis_variance"),
                        "ml_prior_variance": unc.get("ml_prior_variance"),
                    },
                }
            )
        er_path = Path(args.output_enriched_records_json)
        er_path.parent.mkdir(parents=True, exist_ok=True)
        er_path.write_text(json.dumps(enriched_rows, indent=2), encoding="utf-8")
        print(f"Saved enriched rows: {er_path}")

    print(f"Saved: {out_path}")
    print(f"Records: {len(records)}")
    print("U mode:", args.u_mode)
    if args.u_mode == "learned":
        lm = (out.get("composite_definition", {}).get("metrics", {}) or {})
        print("Learned predictor AUC:", lm.get("all", {}).get("auc"))
        print("Learned split AUC:", "train=", lm.get("train", {}).get("auc"), "val=", lm.get("val", {}).get("auc"), "test=", lm.get("test", {}).get("auc"))
    print(
        "Overall correlation (U,error):",
        f"pearson={out['validation']['with_signal']['all']['pearson_u_error']:.6f}",
        f"spearman={out['validation']['with_signal']['all']['spearman_u_error']:.6f}",
    )
    print(
        "Target stats:",
        "mean_score=",
        out["validation"]["with_signal"]["all"]["mean_score"],
        "high_error_rate=",
        out["validation"]["with_signal"]["all"]["high_error_rate"],
        "definition=",
        out["validation"]["with_signal"]["all"]["high_error_definition"],
    )
    print(
        "Overall ROC AUC(U->error):",
        out["validation"]["with_signal"]["all"]["roc_auc_u_predicts_error"],
        f"({out['validation']['with_signal']['all']['auc_quality']})",
    )
    print(
        "Top decile error rate:",
        out["validation"]["with_signal"]["all"]["top_decile_error_rate"],
        f"(n={out['validation']['with_signal']['all']['top_decile_n']})",
        "ratio=",
        out["validation"]["with_signal"]["all"]["top_decile_error_concentration_ratio"],
    )
    print(
        "Top 20% error rate:",
        out["validation"]["with_signal"]["all"]["top_quintile_error_rate"],
        f"(n={out['validation']['with_signal']['all']['top_quintile_n']})",
        "ratio=",
        out["validation"]["with_signal"]["all"]["top_quintile_error_concentration_ratio"],
    )
    print(
        "Higher-U lower-accuracy support:",
        out["validation"]["with_signal"]["all"]["supports_higher_u_lower_accuracy"],
    )


if __name__ == "__main__":
    main()
