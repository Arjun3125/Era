#!/usr/bin/env python
"""
Evaluate Phase 2 gating success criteria and emit pass/fail report.

Default criteria:
- Core lift >= +0.05 absolute
- OOD lift >= 0.0
- Core effect size >= 0.5
- No calibration collapse
- No minister collapse (when gating is enabled)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

EPS = 1e-9


def _load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _get_float(d: Dict[str, Any], key: str) -> Optional[float]:
    value = d.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _ge_with_tol(value: Optional[float], threshold: float, eps: float = EPS) -> bool:
    return value is not None and value >= (threshold - eps)


def _le_with_tol(value: Optional[float], threshold: float, eps: float = EPS) -> bool:
    return value is not None and value <= (threshold + eps)


def evaluate_gates(
    candidate: Dict[str, Any],
    *,
    baseline_reference: Optional[Dict[str, Any]],
    core_lift_threshold: float,
    ood_lift_threshold: float,
    effect_size_threshold: float,
    calibration_tolerance: float,
    max_mean_minister_weight_threshold: float,
) -> Dict[str, Any]:
    core = candidate.get("core", {}) or {}
    stress = candidate.get("stress", {}) or {}
    ood = stress.get("ood", {}) or {}

    core_lift = _get_float(core, "mean_difference")
    core_d = _get_float(core, "cohens_d")
    ood_lift = _get_float(ood, "mean_difference")
    core_ece = _get_float(core, "ece")
    core_brier = _get_float(core, "brier")
    core_ece_raw = _get_float(core, "ece_raw")
    core_brier_raw = _get_float(core, "brier_raw")
    metadata = candidate.get("metadata", {}) or {}
    gating_enabled = bool(metadata.get("gating_enabled", False))
    gating_weight_stats = metadata.get("gating_weight_stats", {}) or {}
    max_mean_minister_weight = _get_float(gating_weight_stats, "max_mean_weight")

    checks = []
    checks.append(
        {
            "name": "core_lift_absolute",
            "threshold": core_lift_threshold,
            "actual": core_lift,
            "passed": _ge_with_tol(core_lift, core_lift_threshold),
            "reason": "Core lift must meet configured minimum.",
        }
    )
    checks.append(
        {
            "name": "ood_negative_lift_eliminated",
            "threshold": ood_lift_threshold,
            "actual": ood_lift,
            "passed": _ge_with_tol(ood_lift, ood_lift_threshold),
            "reason": "OOD lift must meet configured minimum.",
        }
    )
    checks.append(
        {
            "name": "core_effect_size",
            "threshold": effect_size_threshold,
            "actual": core_d,
            "passed": _ge_with_tol(core_d, effect_size_threshold),
            "reason": "Core effect size must meet configured minimum.",
        }
    )

    if baseline_reference:
        base_core = baseline_reference.get("core", {}) or {}
        base_ece = _get_float(base_core, "ece")
        base_brier = _get_float(base_core, "brier")
        calibration_pass = (
            core_ece is not None and base_ece is not None
            and _le_with_tol(core_ece, base_ece + calibration_tolerance)
        )
        calibration_detail = {
            "mode": "relative_to_baseline",
            "candidate_ece": core_ece,
            "candidate_brier": core_brier,
            "baseline_ece": base_ece,
            "baseline_brier": base_brier,
            "tolerance": calibration_tolerance,
        }
    else:
        calibration_pass = (
            core_ece is not None and core_ece_raw is not None
            and _le_with_tol(core_ece, core_ece_raw + calibration_tolerance)
        )
        calibration_detail = {
            "mode": "self_sanity_vs_raw",
            "candidate_ece": core_ece,
            "candidate_brier": core_brier,
            "raw_ece": core_ece_raw,
            "raw_brier": core_brier_raw,
            "tolerance": calibration_tolerance,
        }

    checks.append(
        {
            "name": "no_calibration_collapse",
            "threshold": "candidate_ece <= baseline/raw(+tol)",
            "actual": calibration_detail,
            "passed": calibration_pass,
            "reason": "Calibrated reliability must not regress.",
        }
    )

    collapse_actual: Dict[str, Any] = {
        "gating_enabled": gating_enabled,
        "max_mean_weight": max_mean_minister_weight,
    }
    if gating_enabled:
        collapse_pass = (
            max_mean_minister_weight is not None
            and max_mean_minister_weight < max_mean_minister_weight_threshold
        )
    else:
        collapse_pass = True
        collapse_actual["note"] = "check_skipped_gating_disabled"

    checks.append(
        {
            "name": "no_minister_collapse",
            "threshold": f"max_mean_weight < {max_mean_minister_weight_threshold}",
            "actual": collapse_actual,
            "passed": collapse_pass,
            "reason": "No single minister should dominate average gating weights.",
        }
    )

    all_passed = all(item["passed"] for item in checks)
    summary = {
        "decision": "PASS" if all_passed else "REVERT",
        "all_passed": all_passed,
        "failed_checks": [c["name"] for c in checks if not c["passed"]],
    }

    return {
        "metadata": {
            "evaluated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_phase_timestamp": candidate.get("metadata", {}).get("timestamp_utc"),
        },
        "checks": checks,
        "summary": summary,
    }


def write_markdown(report: Dict[str, Any], path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 2 Gate Report",
        "",
        f"- Evaluated UTC: {report['metadata']['evaluated_utc']}",
        f"- Candidate Timestamp: {report['metadata']['candidate_phase_timestamp']}",
        f"- Decision: **{report['summary']['decision']}**",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {check['name']}: {status}")
        lines.append(f"  - threshold: {check['threshold']}")
        lines.append(f"  - actual: {check['actual']}")
        lines.append(f"  - reason: {check['reason']}")
    if report["summary"]["failed_checks"]:
        lines.append("")
        lines.append("## Failed Checks")
        for name in report["summary"]["failed_checks"]:
            lines.append(f"- {name}")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Phase 2 gate criteria")
    parser.add_argument(
        "--candidate",
        default="evaluation/results/phase2_robustness_results.json",
        help="Candidate Phase2 results JSON",
    )
    parser.add_argument(
        "--baseline-reference",
        default=None,
        help="Optional baseline Phase2 results JSON for relative no-collapse checks",
    )
    parser.add_argument(
        "--core-lift-threshold",
        type=float,
        default=0.0792,
        help="Minimum required absolute lift on core",
    )
    parser.add_argument(
        "--effect-size-threshold",
        type=float,
        default=0.7,
        help="Minimum required core effect size",
    )
    parser.add_argument(
        "--ood-lift-threshold",
        type=float,
        default=0.02,
        help="Minimum required absolute lift on OOD",
    )
    parser.add_argument(
        "--calibration-tolerance",
        type=float,
        default=0.02,
        help="Allowed positive regression tolerance for calibration checks",
    )
    parser.add_argument(
        "--max-mean-minister-weight-threshold",
        type=float,
        default=0.85,
        help="Maximum allowed mean weight for any single minister when gating is enabled",
    )
    parser.add_argument(
        "--output-json",
        default="evaluation/results/phase2_gate_report.json",
        help="Output report JSON path",
    )
    parser.add_argument(
        "--output-md",
        default="evaluation/results/PHASE2_GATE_REPORT.md",
        help="Output report markdown path",
    )
    args = parser.parse_args()

    candidate = _load_json(args.candidate)
    baseline_reference = _load_json(args.baseline_reference) if args.baseline_reference else None
    report = evaluate_gates(
        candidate,
        baseline_reference=baseline_reference,
        core_lift_threshold=args.core_lift_threshold,
        ood_lift_threshold=args.ood_lift_threshold,
        effect_size_threshold=args.effect_size_threshold,
        calibration_tolerance=args.calibration_tolerance,
        max_mean_minister_weight_threshold=args.max_mean_minister_weight_threshold,
    )

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, args.output_md)

    print(f"Saved JSON report: {out_json}")
    print(f"Saved Markdown report: {args.output_md}")
    print(f"Decision: {report['summary']['decision']}")
    if report["summary"]["failed_checks"]:
        print("Failed checks:")
        for check in report["summary"]["failed_checks"]:
            print(f"- {check}")


if __name__ == "__main__":
    main()
