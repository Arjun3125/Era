#!/usr/bin/env python
"""
Reliability analysis and split-safe calibration workflow.

Implements:
- Reliability bins (10)
- ECE, MCE, Brier, overconfidence bias
- Per-distribution analysis: core, ood, adv, combined
- Train/val/test calibration with no leakage:
  - cross-fitted isotonic regression (fit on train, select on val)
  - temperature scaling (fit on train, select on val)
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

from evaluation.metrics.evaluation_metrics import EvaluationMetrics


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
    correct = int(record.get("correct", record.get("outcome", 0)))
    sid = str(record.get("scenario_id", ""))
    distribution = str(record.get("distribution", record.get("distribution_type", ""))).strip().lower()
    if not distribution or distribution == "unknown":
        distribution = _infer_distribution_from_scenario_id(sid)
    if distribution == "adversarial":
        distribution = "adv"
    split = str(record.get("split", "unspecified")).strip().lower() or "unspecified"
    return {
        "confidence": confidence,
        "correct": int(1 if correct else 0),
        "scenario_id": sid,
        "split": split,
        "distribution": distribution,
        "run_name": str(record.get("run_name", default_run_name)),
        "seed": record.get("seed"),
    }


def _reconstruct_records_from_run_payload(run_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    run_name = str(run_payload.get("run_name", "unknown"))
    if isinstance(run_payload.get("confidence_records"), list):
        return [_normalize_record(r, default_run_name=run_name) for r in run_payload["confidence_records"]]

    reconstructed: List[Dict[str, Any]] = []
    conf_by_seed = run_payload.get("scenario_confidence_by_seed", {}) or {}
    out_by_seed = run_payload.get("scenario_outcome_by_seed", {}) or {}
    split_name = str(run_payload.get("split_name", "unspecified")).strip().lower() or "unspecified"
    for seed_key, conf_map in conf_by_seed.items():
        outcomes = out_by_seed.get(seed_key, {}) or {}
        seed_val: Any = seed_key
        if isinstance(seed_key, str) and seed_key.startswith("seed_"):
            try:
                seed_val = int(seed_key.split("_", 1)[1])
            except Exception:
                seed_val = seed_key
        for sid, conf in (conf_map or {}).items():
            reconstructed.append(
                _normalize_record(
                    {
                        "confidence": conf,
                        "correct": int((outcomes or {}).get(sid, 0)),
                        "scenario_id": sid,
                        "split": split_name,
                        "run_name": run_name,
                        "seed": seed_val,
                    },
                    default_run_name=run_name,
                )
            )
    return reconstructed


def _load_records_from_result(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: List[Dict[str, Any]] = []

    if isinstance(payload.get("confidence_records"), list):
        records.extend(_normalize_record(r) for r in payload["confidence_records"])

    if isinstance(payload.get("raw_runs"), dict):
        for run_payload in payload["raw_runs"].values():
            if isinstance(run_payload, dict):
                records.extend(_reconstruct_records_from_run_payload(run_payload))

    if isinstance(payload.get("runs"), dict):
        for run_payload in payload["runs"].values():
            if isinstance(run_payload, dict):
                records.extend(_reconstruct_records_from_run_payload(run_payload))

    if not records:
        records.extend(_reconstruct_records_from_run_payload(payload))
    return records


def load_records(paths: Iterable[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for raw_path in paths:
        p = Path(raw_path)
        if not p.exists():
            raise FileNotFoundError(f"Result JSON not found: {p}")
        records.extend(_load_records_from_result(p))
    return records


def _load_split_lookup(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Split manifest not found: {path}")
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
                if existing and existing != str(split_name):
                    raise RuntimeError(
                        f"Scenario '{sid_str}' is assigned to multiple splits: {existing}, {split_name}"
                    )
                lookup[sid_str] = str(split_name).lower()
    return lookup


def _apply_split_lookup(records: List[Dict[str, Any]], lookup: Dict[str, str]) -> None:
    for rec in records:
        split = str(rec.get("split", "unspecified")).strip().lower() or "unspecified"
        if split not in {"unspecified", "unknown", ""}:
            continue
        sid = str(rec.get("scenario_id", ""))
        if sid in lookup:
            rec["split"] = lookup[sid]


def _compute_reliability_metrics(records: List[Dict[str, Any]], n_bins: int = 10) -> Dict[str, Any]:
    if not records:
        return {
            "n": 0,
            "ece": 0.0,
            "mce": 0.0,
            "brier": 0.0,
            "overconfidence_bias": 0.0,
            "mean_confidence": 0.0,
            "accuracy": 0.0,
            "bins": [],
        }

    conf = np.asarray([float(r["confidence"]) for r in records], dtype=float)
    corr = np.asarray([int(r["correct"]) for r in records], dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)

    ece = 0.0
    mce = 0.0
    bins: List[Dict[str, Any]] = []
    for i in range(n_bins):
        lo = float(edges[i])
        hi = float(edges[i + 1])
        if i == n_bins - 1:
            mask = (conf >= lo) & (conf <= hi)
        else:
            mask = (conf >= lo) & (conf < hi)
        count = int(np.sum(mask))
        if count == 0:
            bins.append(
                {
                    "bin_index": i,
                    "range": [lo, hi],
                    "count": 0,
                    "mean_confidence": None,
                    "accuracy": None,
                    "gap": None,
                }
            )
            continue
        c_mean = float(np.mean(conf[mask]))
        a_mean = float(np.mean(corr[mask]))
        gap = abs(c_mean - a_mean)
        ece += (count / len(conf)) * gap
        mce = max(mce, gap)
        bins.append(
            {
                "bin_index": i,
                "range": [lo, hi],
                "count": count,
                "mean_confidence": c_mean,
                "accuracy": a_mean,
                "gap": float(c_mean - a_mean),
            }
        )

    brier = float(np.mean((conf - corr) ** 2))
    overconfidence_bias = float(np.mean(conf - corr))
    return {
        "n": int(len(records)),
        "ece": float(ece),
        "mce": float(mce),
        "brier": brier,
        "overconfidence_bias": overconfidence_bias,
        "mean_confidence": float(np.mean(conf)),
        "accuracy": float(np.mean(corr)),
        "bins": bins,
    }


def _split_by_distribution(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped = {
        "core": [],
        "ood": [],
        "adv": [],
        "combined": list(records),
    }
    for r in records:
        d = str(r.get("distribution", "unknown")).lower()
        if d in grouped:
            grouped[d].append(r)
    return grouped


def _apply_temperature(conf: np.ndarray, temperature: float) -> np.ndarray:
    conf = np.clip(conf, 1e-6, 1.0 - 1e-6)
    logits = np.log(conf / (1.0 - conf))
    scaled = 1.0 / (1.0 + np.exp(-(logits / max(float(temperature), 1e-6))))
    return np.clip(scaled, 0.0, 1.0)


def _fit_temperature(train_conf: np.ndarray, train_corr: np.ndarray) -> float:
    grid = np.exp(np.linspace(math.log(0.25), math.log(6.0), 300))
    best_t = 1.0
    best_nll = float("inf")
    y = np.clip(train_corr, 0.0, 1.0)
    for t in grid:
        p = np.clip(_apply_temperature(train_conf, float(t)), 1e-6, 1.0 - 1e-6)
        nll = float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))
        if nll < best_nll:
            best_nll = nll
            best_t = float(t)
    return float(best_t)


def _apply_isotonic_model(conf: np.ndarray, model: Dict[str, Any]) -> np.ndarray:
    xt = np.asarray(model.get("x_thresholds", []), dtype=float)
    yt = np.asarray(model.get("y_thresholds", []), dtype=float)
    if xt.size == 0 or yt.size == 0:
        return np.clip(conf, 0.0, 1.0)
    pred = np.interp(conf, xt, yt, left=float(yt[0]), right=float(yt[-1]))
    return np.clip(pred, 0.0, 1.0)


def _fit_and_select_calibrator(
    train_records: List[Dict[str, Any]],
    val_records: List[Dict[str, Any]],
    *,
    method: str,
) -> Dict[str, Any]:
    train_conf = np.asarray([r["confidence"] for r in train_records], dtype=float)
    train_corr = np.asarray([r["correct"] for r in train_records], dtype=float)
    val_conf = np.asarray([r["confidence"] for r in val_records], dtype=float)
    val_corr = np.asarray([r["correct"] for r in val_records], dtype=float)

    metrics = EvaluationMetrics()
    method = method.lower().strip()
    candidates: Dict[str, Dict[str, Any]] = {
        "identity": {
            "name": "identity",
            "val_ece": float(metrics.compute_ece(val_conf.tolist(), val_corr.astype(int).tolist())),
            "val_brier": float(metrics.compute_brier(val_conf.tolist(), val_corr.astype(int).tolist())),
            "artifact": {},
        }
    }

    iso_fit = metrics.apply_isotonic_regression_crossfit(
        train_conf.tolist(),
        train_corr.astype(int).tolist(),
        n_folds=5,
        random_seed=42,
    )
    iso_model = iso_fit["global_model"]
    val_iso = _apply_isotonic_model(val_conf, iso_model)
    candidates["isotonic"] = {
        "name": "isotonic",
        "val_ece": float(metrics.compute_ece(val_iso.tolist(), val_corr.astype(int).tolist())),
        "val_brier": float(metrics.compute_brier(val_iso.tolist(), val_corr.astype(int).tolist())),
        "artifact": {"model": iso_model},
    }

    temp = _fit_temperature(train_conf, train_corr)
    val_temp = _apply_temperature(val_conf, temp)
    candidates["temperature"] = {
        "name": "temperature",
        "val_ece": float(metrics.compute_ece(val_temp.tolist(), val_corr.astype(int).tolist())),
        "val_brier": float(metrics.compute_brier(val_temp.tolist(), val_corr.astype(int).tolist())),
        "artifact": {"temperature": temp},
    }

    if method in {"isotonic", "temperature", "identity"}:
        selected = candidates[method]
    else:
        selected = min(candidates.values(), key=lambda x: (x["val_ece"], x["val_brier"]))

    return {
        "selected": selected,
        "candidates": candidates,
    }


def _apply_calibrator_to_records(records: List[Dict[str, Any]], selected: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = str(selected.get("name", "identity"))
    calibrated = [dict(r) for r in records]
    conf = np.asarray([r["confidence"] for r in calibrated], dtype=float)
    if name == "isotonic":
        pred = _apply_isotonic_model(conf, selected.get("artifact", {}).get("model", {}))
    elif name == "temperature":
        pred = _apply_temperature(conf, float(selected.get("artifact", {}).get("temperature", 1.0)))
    else:
        pred = np.clip(conf, 0.0, 1.0)
    for i, r in enumerate(calibrated):
        r["confidence"] = float(pred[i])
    return calibrated


def _plot_reliability(metrics_by_dist: Dict[str, Dict[str, Any]], output_path: Path, title: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        _plot_reliability_svg(metrics_by_dist, output_path.with_suffix(".svg"), title)
        return

    dists = ["core", "ood", "adv", "combined"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 9), constrained_layout=True)
    axes = axes.flatten()
    for idx, dist in enumerate(dists):
        ax = axes[idx]
        data = metrics_by_dist.get(dist, {})
        bins = data.get("bins", [])
        xs = [b["mean_confidence"] for b in bins if b.get("mean_confidence") is not None]
        ys = [b["accuracy"] for b in bins if b.get("accuracy") is not None]
        cs = [b["count"] for b in bins if b.get("count")]
        ax.plot([0, 1], [0, 1], "--", color="gray", linewidth=1)
        if xs and ys:
            ax.plot(xs, ys, marker="o", color="#1f77b4", linewidth=1.5)
            ax.scatter(xs, ys, s=[max(20, c * 2) for c in cs], alpha=0.65, color="#1f77b4")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Predicted Confidence")
        ax.set_ylabel("Empirical Accuracy")
        ax.set_title(
            f"{dist.upper()} | n={data.get('n', 0)} | ECE={data.get('ece', 0.0):.3f} | MCE={data.get('mce', 0.0):.3f}"
        )
        ax.grid(alpha=0.25)
    fig.suptitle(title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def _xml_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _plot_reliability_svg(
    metrics_by_dist: Dict[str, Dict[str, Any]],
    output_path: Path,
    title: str,
) -> None:
    """
    Dependency-free SVG fallback when matplotlib is unavailable.
    """
    dists = ["core", "ood", "adv", "combined"]
    width = 1200
    height = 920
    margin = 36
    panel_w = (width - margin * 3) // 2
    panel_h = (height - margin * 3) // 2
    pad_left = 58
    pad_right = 16
    pad_top = 28
    pad_bottom = 44

    def panel_xy(idx: int) -> tuple[int, int]:
        row = idx // 2
        col = idx % 2
        x0 = margin + col * (panel_w + margin)
        y0 = margin + 40 + row * (panel_h + margin)
        return x0, y0

    def map_point(x0: int, y0: int, u: float, acc: float) -> tuple[float, float]:
        inner_w = panel_w - pad_left - pad_right
        inner_h = panel_h - pad_top - pad_bottom
        px = x0 + pad_left + float(u) * inner_w
        py = y0 + pad_top + (1.0 - float(acc)) * inner_h
        return px, py

    parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" fill="#111">{_xml_escape(title)}</text>',
    ]

    for idx, dist in enumerate(dists):
        x0, y0 = panel_xy(idx)
        inner_w = panel_w - pad_left - pad_right
        inner_h = panel_h - pad_top - pad_bottom
        x1 = x0 + panel_w
        y1 = y0 + panel_h
        ax_left = x0 + pad_left
        ax_top = y0 + pad_top
        ax_right = ax_left + inner_w
        ax_bottom = ax_top + inner_h

        data = metrics_by_dist.get(dist, {}) or {}
        bins = data.get("bins", []) or []
        points = [
            (float(b["mean_confidence"]), float(b["accuracy"]), int(b["count"]))
            for b in bins
            if b.get("mean_confidence") is not None and b.get("accuracy") is not None
        ]

        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{panel_h}" fill="none" stroke="#d0d0d0" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x0 + panel_w/2:.1f}" y="{y0 + 18}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#111">{dist.upper()} | n={int(data.get("n", 0))} | ECE={float(data.get("ece", 0.0)):.3f} | MCE={float(data.get("mce", 0.0)):.3f}</text>'
        )
        # Axes
        parts.append(f'<line x1="{ax_left}" y1="{ax_bottom}" x2="{ax_right}" y2="{ax_bottom}" stroke="#888" stroke-width="1"/>')
        parts.append(f'<line x1="{ax_left}" y1="{ax_top}" x2="{ax_left}" y2="{ax_bottom}" stroke="#888" stroke-width="1"/>')
        # Diagonal
        parts.append(f'<line x1="{ax_left}" y1="{ax_bottom}" x2="{ax_right}" y2="{ax_top}" stroke="#aaaaaa" stroke-dasharray="5,4" stroke-width="1"/>')
        # Labels
        parts.append(
            f'<text x="{x0 + panel_w/2:.1f}" y="{y1 - 10}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#444">Predicted Confidence</text>'
        )
        parts.append(
            f'<text x="{x0 + 14}" y="{y0 + panel_h/2:.1f}" text-anchor="middle" transform="rotate(-90 {x0 + 14} {y0 + panel_h/2:.1f})" font-family="Arial, sans-serif" font-size="11" fill="#444">Empirical Accuracy</text>'
        )

        if points:
            poly = []
            for u, acc, _ in points:
                px, py = map_point(x0, y0, u, acc)
                poly.append(f"{px:.2f},{py:.2f}")
            parts.append(
                f'<polyline points="{" ".join(poly)}" fill="none" stroke="#1f77b4" stroke-width="2"/>'
            )
            for u, acc, count in points:
                px, py = map_point(x0, y0, u, acc)
                radius = max(3.0, min(12.0, 2.0 + (count ** 0.5)))
                parts.append(
                    f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{radius:.2f}" fill="#1f77b4" fill-opacity="0.35" stroke="#1f77b4" stroke-width="1"/>'
                )

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reliability analysis + split-safe calibration")
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="One or more results JSON files (evaluation/phase2/benchmark exports).",
    )
    parser.add_argument(
        "--include-run-names",
        default=None,
        help="Optional comma-separated run_name allowlist (e.g., phase2_core_council,phase2_ood_council).",
    )
    parser.add_argument("--n-bins", type=int, default=10)
    parser.add_argument("--output-dir", default="evaluation/results/reliability")
    parser.add_argument("--output-json", default="reliability_analysis.json")
    parser.add_argument("--method", choices=["auto", "isotonic", "temperature", "identity"], default="auto")
    parser.add_argument("--target-ece", type=float, default=0.05)
    parser.add_argument("--split-train", default="train")
    parser.add_argument("--split-val", default="val")
    parser.add_argument("--split-test", default="test")
    parser.add_argument(
        "--split-manifest",
        default=None,
        help="Optional split manifest to backfill split labels by scenario_id when records have split=unspecified.",
    )
    parser.add_argument("--skip-calibration", action="store_true")
    args = parser.parse_args()

    records = load_records(args.inputs)
    if args.split_manifest:
        split_lookup = _load_split_lookup(Path(args.split_manifest))
        _apply_split_lookup(records, split_lookup)
    if args.include_run_names:
        allow = {x.strip() for x in args.include_run_names.split(",") if x.strip()}
        records = [r for r in records if r.get("run_name") in allow]
    if not records:
        raise RuntimeError("No confidence records found in provided inputs.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_grouped = _split_by_distribution(records)
    raw_metrics = {dist: _compute_reliability_metrics(rows, n_bins=args.n_bins) for dist, rows in raw_grouped.items()}
    _plot_reliability(raw_metrics, output_dir / "reliability_raw.png", "Reliability Diagram (Raw)")

    analysis: Dict[str, Any] = {
        "metadata": {
            "n_records": len(records),
            "n_bins": int(args.n_bins),
            "inputs": args.inputs,
            "method": args.method,
            "target_ece": float(args.target_ece),
        },
        "raw": {
            "metrics": raw_metrics,
        },
    }

    if not args.skip_calibration:
        train_split = str(args.split_train).lower()
        val_split = str(args.split_val).lower()
        test_split = str(args.split_test).lower()
        train_records = [r for r in records if r.get("split") == train_split]
        val_records = [r for r in records if r.get("split") == val_split]
        test_records = [r for r in records if r.get("split") == test_split]
        if not train_records or not val_records or not test_records:
            raise RuntimeError(
                "Calibration requires split-labeled records for train/val/test. "
                "Run evaluations with split labels first."
            )

        raw_test_metrics = _compute_reliability_metrics(test_records, n_bins=args.n_bins)
        selection = _fit_and_select_calibrator(
            train_records,
            val_records,
            method=args.method,
        )
        selected = selection["selected"]
        apply_calibration = raw_test_metrics["ece"] > float(args.target_ece)
        if not apply_calibration:
            selected = selection["candidates"]["identity"]

        calibrated_test_records = _apply_calibrator_to_records(test_records, selected)
        cal_grouped = _split_by_distribution(calibrated_test_records)
        cal_metrics = {dist: _compute_reliability_metrics(rows, n_bins=args.n_bins) for dist, rows in cal_grouped.items()}
        _plot_reliability(cal_metrics, output_dir / "reliability_calibrated_test.png", "Reliability Diagram (Calibrated Test)")

        analysis["calibration"] = {
            "splits": {
                "train": len(train_records),
                "val": len(val_records),
                "test": len(test_records),
            },
            "selection": selection,
            "applied": bool(apply_calibration),
            "selected_method": selected["name"],
            "raw_test_metrics": _split_by_distribution(test_records),
            "calibrated_test_metrics": cal_metrics,
        }
        # Replace raw_test_metrics payload with computed metrics to keep JSON compact.
        analysis["calibration"]["raw_test_metrics"] = {
            dist: _compute_reliability_metrics(rows, n_bins=args.n_bins)
            for dist, rows in _split_by_distribution(test_records).items()
        }

    out_path = output_dir / args.output_json
    out_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"Saved reliability analysis: {out_path}")
    print(f"Total records: {len(records)}")
    print(f"Raw combined ECE: {analysis['raw']['metrics']['combined']['ece']:.6f}")
    if not args.skip_calibration and "calibration" in analysis:
        selected_method = analysis["calibration"]["selected_method"]
        raw_ece = analysis["calibration"]["raw_test_metrics"]["combined"]["ece"]
        cal_ece = analysis["calibration"]["calibrated_test_metrics"]["combined"]["ece"]
        print(f"Calibration method: {selected_method}")
        print(f"Test ECE raw -> calibrated: {raw_ece:.6f} -> {cal_ece:.6f}")


if __name__ == "__main__":
    main()
