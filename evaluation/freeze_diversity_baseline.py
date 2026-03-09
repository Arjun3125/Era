#!/usr/bin/env python
"""
Freeze and tag the diversity baseline configuration/state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 64)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze ERA diversity baseline")
    parser.add_argument("--tag", default="ERA_v2.0_diversity_baseline")
    parser.add_argument(
        "--phase2-results",
        default="evaluation/results/phase2_robustness_results.json",
    )
    parser.add_argument(
        "--phase2-report",
        default="evaluation/results/PHASE2_ROBUSTNESS_REPORT.md",
    )
    parser.add_argument(
        "--split-manifest",
        default="evaluation/benchmark_dataset/split_manifest_seed42.json",
    )
    parser.add_argument(
        "--gate-threshold-core-lift",
        type=float,
        default=0.0792,
    )
    parser.add_argument(
        "--gate-threshold-core-d",
        type=float,
        default=0.7,
    )
    parser.add_argument(
        "--gate-threshold-ood-lift",
        type=float,
        default=0.02,
    )
    parser.add_argument(
        "--gate-threshold-max-mean-minister-weight",
        type=float,
        default=0.85,
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation/baselines/ERA_v2.0_diversity_baseline",
    )
    args = parser.parse_args()

    phase2_results_path = Path(args.phase2_results)
    phase2_report_path = Path(args.phase2_report)
    split_manifest_path = Path(args.split_manifest)
    run_script_path = Path("evaluation/run_phase2_robustness.py")

    for p in [phase2_results_path, phase2_report_path, split_manifest_path, run_script_path]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {p}")

    phase2_results = _read_json(phase2_results_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lock = {
        "tag": args.tag,
        "frozen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_version": {
            "user_model": "deepseek-r1:8b",
            "eval_num_predict": 256,
            "eval_think_off": True,
            "eval_request_timeout_seconds": 120,
        },
        "diversity_prompt": {
            "enabled": True,
            "template_source_file": str(run_script_path),
            "template_source_sha256": _sha256(run_script_path),
            "template_excerpt": "MINISTER_RISK / MINISTER_OPTIONALITY / MINISTER_EXECUTION / MINISTER_ADVERSARY format",
        },
        "calibration": {
            "method": "pair_adjacent_violators_crossfit",
            "crossfit_folds": 5,
        },
        "dataset_split_manifest": {
            "path": str(split_manifest_path),
            "sha256": _sha256(split_manifest_path),
        },
        "phase2_gate_thresholds_for_gating": {
            "core_lift_gt": args.gate_threshold_core_lift,
            "core_effect_size_gte": args.gate_threshold_core_d,
            "ood_lift_gte": args.gate_threshold_ood_lift,
            "max_mean_minister_weight_lt": args.gate_threshold_max_mean_minister_weight,
            "calibration_not_worse_than_baseline": True,
        },
        "baseline_metrics": phase2_results.get("core", {}),
        "stress_metrics": phase2_results.get("stress", {}),
    }

    lock_path = output_dir / "baseline_lock.json"
    lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")

    (output_dir / "TAG.txt").write_text(args.tag + "\n", encoding="utf-8")
    (output_dir / "phase2_robustness_results.json").write_text(
        phase2_results_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (output_dir / "PHASE2_ROBUSTNESS_REPORT.md").write_text(
        phase2_report_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (output_dir / split_manifest_path.name).write_text(
        split_manifest_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    print(f"Frozen baseline: {lock_path}")
    print(f"Tag: {args.tag}")


if __name__ == "__main__":
    main()
