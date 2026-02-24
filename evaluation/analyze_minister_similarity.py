#!/usr/bin/env python
"""
Build minister similarity matrices and compare core vs OOD structure.

Outputs:
- evaluation/results/minister_similarity_report.json
- evaluation/results/MINISTER_SIMILARITY_REPORT.md
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.scoring.rubric_engine import RubricEngine
from persona.council import CouncilAggregator

CORE_CATEGORIES = {"irreversible", "emotional", "strategic", "long_horizon"}
OOD_CATEGORY = "out_of_distribution"
STANCE_TO_NUM = {"oppose": -1.0, "neutral": 0.0, "support": 1.0}


def _safe_pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size == 0 or y.size == 0:
        return 0.0
    x_std = float(np.std(x))
    y_std = float(np.std(y))
    if x_std == 0.0 or y_std == 0.0:
        return 1.0 if np.array_equal(x, y) else 0.0
    corr = float(np.corrcoef(x, y)[0, 1])
    if math.isnan(corr):
        return 0.0
    return corr


def _filter_dataset(all_scenarios: Dict[str, Dict], dataset: str) -> Dict[str, Dict]:
    if dataset == "core":
        return {
            sid: s for sid, s in all_scenarios.items()
            if s.get("category") in CORE_CATEGORIES
        }
    if dataset == "ood":
        return {
            sid: s for sid, s in all_scenarios.items()
            if s.get("category") == OOD_CATEGORY
        }
    raise ValueError(f"Unsupported dataset: {dataset}")


def _collect_stance_vectors(
    scenarios: Dict[str, Dict],
    council: CouncilAggregator,
) -> Dict[str, List[float]]:
    vectors: Dict[str, List[float]] = {name: [] for name in council.ministers.keys()}
    scenario_ids = sorted(scenarios.keys())
    for sid in scenario_ids:
        scenario = scenarios[sid]
        user_input = scenario.get("input", "")
        context = {
            "domains": scenario.get("domains", []),
            "category": scenario.get("category"),
            "turn_count": 1,
            "recent_turns": [],
        }
        for minister_name, minister in council.ministers.items():
            try:
                position = minister.analyze(user_input, context)
                stance = str(getattr(position, "stance", "neutral")).lower()
                vectors[minister_name].append(STANCE_TO_NUM.get(stance, 0.0))
            except Exception:
                vectors[minister_name].append(0.0)
    return vectors


def _similarity_matrices(vectors: Dict[str, List[float]]) -> Dict[str, Dict[str, Dict[str, float]]]:
    names = list(vectors.keys())
    arr = {name: np.array(vectors[name], dtype=float) for name in names}
    agreement: Dict[str, Dict[str, float]] = {}
    correlation: Dict[str, Dict[str, float]] = {}

    for a in names:
        agreement[a] = {}
        correlation[a] = {}
        for b in names:
            va = arr[a]
            vb = arr[b]
            if va.size == 0 or vb.size == 0:
                agreement[a][b] = 0.0
                correlation[a][b] = 0.0
                continue
            agreement[a][b] = float(np.mean(va == vb))
            correlation[a][b] = _safe_pearson(va, vb)
    return {"agreement": agreement, "correlation": correlation}


def _flatten_upper(matrix: Dict[str, Dict[str, float]], names: List[str]) -> np.ndarray:
    values: List[float] = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            values.append(float(matrix[a][b]))
    return np.array(values, dtype=float)


def _top_pair_drift(
    core_agreement: Dict[str, Dict[str, float]],
    ood_agreement: Dict[str, Dict[str, float]],
    names: List[str],
    k: int = 10,
) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            core_v = float(core_agreement[a][b])
            ood_v = float(ood_agreement[a][b])
            delta = ood_v - core_v
            rows.append(
                {
                    "pair": f"{a}:::{b}",
                    "core_agreement": core_v,
                    "ood_agreement": ood_v,
                    "delta": delta,
                    "abs_delta": abs(delta),
                }
            )
    rows.sort(key=lambda x: x["abs_delta"], reverse=True)
    return rows[:k]


def _write_markdown(report: Dict, out_path: Path) -> None:
    comp = report["comparison"]
    lines = [
        "# Minister Similarity Report",
        "",
        f"- Timestamp (UTC): {report['metadata']['timestamp_utc']}",
        f"- Ministers: {report['metadata']['n_ministers']}",
        f"- Core scenarios: {report['metadata']['n_core_scenarios']}",
        f"- OOD scenarios: {report['metadata']['n_ood_scenarios']}",
        "",
        "## Matrix Correlation (Core vs OOD)",
        f"- Agreement-matrix Pearson: {comp['agreement_matrix_pearson']:.6f}",
        f"- Correlation-matrix Pearson: {comp['correlation_matrix_pearson']:.6f}",
        f"- Mean absolute agreement delta: {comp['mean_abs_agreement_delta']:.6f}",
        "",
        "## Top Pair Drift (Agreement)",
    ]
    for row in report["top_pair_drift"]:
        lines.append(
            f"- {row['pair']}: core={row['core_agreement']:.3f}, "
            f"ood={row['ood_agreement']:.3f}, delta={row['delta']:.3f}"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    benchmark_dir = "evaluation/benchmark_dataset"
    json_out = Path("evaluation/results/minister_similarity_report.json")
    md_out = Path("evaluation/results/MINISTER_SIMILARITY_REPORT.md")

    rubric = RubricEngine(benchmark_dir)
    all_scenarios = rubric.load_all_scenarios()

    core = _filter_dataset(all_scenarios, "core")
    ood = _filter_dataset(all_scenarios, "ood")

    council = CouncilAggregator(llm=None)
    minister_names = list(council.ministers.keys())

    core_vectors = _collect_stance_vectors(core, council)
    ood_vectors = _collect_stance_vectors(ood, council)

    core_mx = _similarity_matrices(core_vectors)
    ood_mx = _similarity_matrices(ood_vectors)

    core_ag_flat = _flatten_upper(core_mx["agreement"], minister_names)
    ood_ag_flat = _flatten_upper(ood_mx["agreement"], minister_names)
    core_corr_flat = _flatten_upper(core_mx["correlation"], minister_names)
    ood_corr_flat = _flatten_upper(ood_mx["correlation"], minister_names)

    comp = {
        "agreement_matrix_pearson": _safe_pearson(core_ag_flat, ood_ag_flat),
        "correlation_matrix_pearson": _safe_pearson(core_corr_flat, ood_corr_flat),
        "mean_abs_agreement_delta": float(np.mean(np.abs(ood_ag_flat - core_ag_flat)))
        if core_ag_flat.size
        else 0.0,
    }
    top_drift = _top_pair_drift(core_mx["agreement"], ood_mx["agreement"], minister_names, k=10)

    report = {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "benchmark_dir": benchmark_dir,
            "n_ministers": len(minister_names),
            "n_core_scenarios": len(core),
            "n_ood_scenarios": len(ood),
            "ministers": minister_names,
        },
        "comparison": comp,
        "top_pair_drift": top_drift,
        "core": core_mx,
        "ood": ood_mx,
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report, md_out)
    print(f"Saved JSON report: {json_out}")
    print(f"Saved Markdown report: {md_out}")
    print(
        "Agreement matrix Pearson(core, ood): "
        f"{report['comparison']['agreement_matrix_pearson']:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
