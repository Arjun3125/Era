#!/usr/bin/env python
"""
Gate Milestone 3 completion from saved artifacts.

Checks:
1) ECE < 0.05 (calibrated)
2) Overconfidence bias < 0.03
3) U predicts error with AUC >= threshold
4) Top-decile error concentration ratio >= target
5) (control stage only) DARBAR-triggered decisions reduce error under high-U cases
6) (control stage only) Core lift within tolerance
7) (control stage only) Adversarial + OOD lift stable or improved
8) (control stage only) DARBAR invocation rate within compute budget
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _collect_council_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    raw = payload.get("raw_runs", {}) or {}
    for key in ("core_council", "adversarial_council", "ood_council"):
        run = raw.get(key, {}) or {}
        rows = run.get("confidence_records", []) or []
        records.extend(rows)
    return records


def _darbar_delta(control_payload: Dict[str, Any], baseline_payload: Dict[str, Any]) -> Dict[str, Any]:
    control_records = _collect_council_records(control_payload)
    baseline_records = _collect_council_records(baseline_payload)
    base_index: Dict[Tuple[str, Any, str], Dict[str, Any]] = {}
    for row in baseline_records:
        key = (str(row.get("scenario_id", "")), row.get("seed"), str(row.get("distribution", "")))
        base_index[key] = row

    matched: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for row in control_records:
        policy = row.get("control_policy", {}) or {}
        if not bool(policy.get("switch_to_darbar", False)):
            continue
        key = (str(row.get("scenario_id", "")), row.get("seed"), str(row.get("distribution", "")))
        if key in base_index:
            matched.append((row, base_index[key]))

    if not matched:
        return {
            "n_darbar_cases": 0,
            "control_error_rate": None,
            "baseline_error_rate": None,
            "error_rate_delta": None,
            "pass": False,
            "reason": "No matched DARBAR-triggered cases found.",
        }

    control_error = 0.0
    baseline_error = 0.0
    for c, b in matched:
        control_error += 1.0 - float(int(c.get("correct", c.get("outcome", 0))))
        baseline_error += 1.0 - float(int(b.get("correct", b.get("outcome", 0))))
    n = float(len(matched))
    control_rate = control_error / n
    baseline_rate = baseline_error / n
    delta = control_rate - baseline_rate
    reduction_fraction = None
    if baseline_rate > 0.0:
        reduction_fraction = float((baseline_rate - control_rate) / baseline_rate)
    return {
        "n_darbar_cases": int(n),
        "control_error_rate": float(control_rate),
        "baseline_error_rate": float(baseline_rate),
        "error_rate_delta": float(delta),
        "error_reduction_fraction": reduction_fraction,
        "pass": bool(control_rate < baseline_rate),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate Milestone 3 completion")
    parser.add_argument(
        "--stage",
        choices=["modeling", "control"],
        default="modeling",
        help="modeling: uncertainty modeling quality only; control: includes DARBAR/lift impact checks.",
    )
    parser.add_argument("--reliability-json", required=True)
    parser.add_argument("--uncertainty-json", required=True)
    parser.add_argument(
        "--uncertainty-scope",
        choices=["auto", "with_signal", "all"],
        default="auto",
        help="Which uncertainty validation slice to gate on.",
    )
    parser.add_argument("--control-phase2-json", default=None)
    parser.add_argument("--baseline-phase2-json", default=None)
    parser.add_argument("--output-json", default="evaluation/results/milestone3_gate_report.json")
    parser.add_argument("--ece-threshold", type=float, default=0.05)
    parser.add_argument("--bias-threshold", type=float, default=0.03)
    parser.add_argument("--auc-threshold", type=float, default=0.65)
    parser.add_argument(
        "--darbar-error-reduction-threshold",
        type=float,
        default=0.20,
        help="Minimum relative error reduction among DARBAR-triggered cases in control stage.",
    )
    parser.add_argument(
        "--core-lift-tolerance",
        type=float,
        default=-0.01,
        help="Allowed control-core-lift delta vs baseline in control stage.",
    )
    parser.add_argument(
        "--max-darbar-invocation-rate",
        type=float,
        default=0.20,
        help="Maximum allowed DARBAR invocation rate in control stage.",
    )
    parser.add_argument(
        "--concentration-mode",
        choices=["relative_max", "absolute"],
        default="relative_max",
        help="relative_max: threshold = frac * (1 / prevalence). absolute: use --concentration-threshold.",
    )
    parser.add_argument(
        "--concentration-threshold",
        type=float,
        default=None,
        help="Absolute required ratio when --concentration-mode absolute.",
    )
    parser.add_argument(
        "--concentration-relative-max-frac",
        type=float,
        default=0.7,
        help="Required fraction of theoretical max concentration (1 / prevalence).",
    )
    args = parser.parse_args()

    reliability = _load_json(args.reliability_json)
    uncertainty = _load_json(args.uncertainty_json)
    control_phase2 = None
    baseline_phase2 = None
    if args.stage == "control":
        if not args.control_phase2_json or not args.baseline_phase2_json:
            raise ValueError("--control-phase2-json and --baseline-phase2-json are required when --stage control")
        control_phase2 = _load_json(args.control_phase2_json)
        baseline_phase2 = _load_json(args.baseline_phase2_json)

    cal = reliability.get("calibration", {}) or {}
    cal_test = cal.get("calibrated_test_metrics", {}) or {}
    cal_combined = cal_test.get("combined", {}) or {}
    ece = float(cal_combined.get("ece", 1.0))
    bias = float(cal_combined.get("overconfidence_bias", 1.0))

    unc_validation = uncertainty.get("validation", {}) or {}
    with_signal_all = ((unc_validation.get("with_signal", {}) or {}).get("all", {}) or {})
    all_all = (unc_validation.get("all", {}) or {})
    if args.uncertainty_scope == "with_signal":
        unc_all = with_signal_all or all_all
    elif args.uncertainty_scope == "all":
        unc_all = all_all or with_signal_all
    else:
        # Default to with_signal when present for continuity with prior milestone reports.
        unc_all = with_signal_all or all_all
    auc = unc_all.get("roc_auc_u_predicts_error")
    auc_val = float(auc) if auc is not None else 0.0
    overall_error_rate = _safe_float(unc_all.get("overall_error_rate"))
    top_decile_error_rate = _safe_float(unc_all.get("top_decile_error_rate"))
    concentration_ratio = _safe_float(unc_all.get("top_decile_error_concentration_ratio"))
    if concentration_ratio is None and overall_error_rate not in (None, 0.0) and top_decile_error_rate is not None:
        concentration_ratio = float(top_decile_error_rate) / float(overall_error_rate)

    theoretical_max = None
    concentration_threshold = None
    if overall_error_rate is not None and overall_error_rate > 0.0:
        theoretical_max = float(1.0 / overall_error_rate)
    if args.concentration_mode == "relative_max":
        if theoretical_max is not None:
            concentration_threshold = float(args.concentration_relative_max_frac * theoretical_max)
    else:
        concentration_threshold = float(args.concentration_threshold) if args.concentration_threshold is not None else 2.5

    darbar: Dict[str, Any] = {
        "n_darbar_cases": 0,
        "control_error_rate": None,
        "baseline_error_rate": None,
        "error_rate_delta": None,
        "pass": None,
        "reason": "Not evaluated in modeling stage.",
    }
    control_core_lift = None
    baseline_core_lift = None
    control_ood_lift = None
    baseline_ood_lift = None
    control_adv_lift = None
    baseline_adv_lift = None
    darbar_invocation_rate = None
    if args.stage == "control" and control_phase2 is not None and baseline_phase2 is not None:
        darbar = _darbar_delta(control_phase2, baseline_phase2)
        control_core_lift = float((control_phase2.get("core", {}) or {}).get("mean_difference", 0.0))
        baseline_core_lift = float((baseline_phase2.get("core", {}) or {}).get("mean_difference", 0.0))
        control_adv_lift = float(
            (((control_phase2.get("stress", {}) or {}).get("adversarial", {}) or {}).get("mean_difference", 0.0))
        )
        baseline_adv_lift = float(
            (((baseline_phase2.get("stress", {}) or {}).get("adversarial", {}) or {}).get("mean_difference", 0.0))
        )
        control_ood_lift = float(
            (((control_phase2.get("stress", {}) or {}).get("ood", {}) or {}).get("mean_difference", 0.0))
        )
        baseline_ood_lift = float(
            (((baseline_phase2.get("stress", {}) or {}).get("ood", {}) or {}).get("mean_difference", 0.0))
        )
        darbar_invocation_rate = _safe_float(
            (((control_phase2.get("metadata", {}) or {}).get("uncertainty_policy_stats", {}) or {}).get("darbar_rate"))
        )

    checks = [
        {
            "name": "calibrated_ece",
            "value": ece,
            "threshold": args.ece_threshold,
            "operator": "<",
            "pass": bool(ece < args.ece_threshold),
        },
        {
            "name": "overconfidence_bias",
            "value": bias,
            "threshold": args.bias_threshold,
            "operator": "<",
            "pass": bool(bias < args.bias_threshold),
        },
        {
            "name": "uncertainty_auc_predicts_error",
            "value": auc,
            "threshold": args.auc_threshold,
            "operator": ">=",
            "pass": bool(auc is not None and auc_val >= args.auc_threshold),
        },
        {
            "name": "uncertainty_top10_error_concentration",
            "value": concentration_ratio,
            "overall_error_rate": overall_error_rate,
            "top_decile_error_rate": top_decile_error_rate,
            "threshold": concentration_threshold,
            "threshold_mode": args.concentration_mode,
            "threshold_relative_max_frac": float(args.concentration_relative_max_frac),
            "theoretical_max": theoretical_max,
            "operator": ">=",
            "pass": bool(
                concentration_ratio is not None
                and concentration_threshold is not None
                and float(concentration_ratio) >= float(concentration_threshold)
            ),
        },
    ]

    if args.stage == "control":
        checks.extend(
            [
                {
                    "name": "darbar_reduces_error_high_u",
                    "value": darbar,
                    "threshold": args.darbar_error_reduction_threshold,
                    "operator": ">=",
                    "pass": bool(
                        (darbar.get("error_reduction_fraction") is not None)
                        and float(darbar.get("error_reduction_fraction")) >= float(args.darbar_error_reduction_threshold)
                    ),
                },
                {
                    "name": "core_lift_within_tolerance",
                    "control_core_lift": control_core_lift,
                    "baseline_core_lift": baseline_core_lift,
                    "operator": ">=",
                    "threshold": args.core_lift_tolerance,
                    "delta": (
                        float(control_core_lift - baseline_core_lift)
                        if (control_core_lift is not None and baseline_core_lift is not None)
                        else None
                    ),
                    "pass": bool(
                        (control_core_lift is not None)
                        and (baseline_core_lift is not None)
                        and ((control_core_lift - baseline_core_lift) >= float(args.core_lift_tolerance))
                    ),
                },
                {
                    "name": "adversarial_lift_stable_or_improved",
                    "control_adv_lift": control_adv_lift,
                    "baseline_adv_lift": baseline_adv_lift,
                    "operator": ">=",
                    "pass": bool(
                        (control_adv_lift is not None)
                        and (baseline_adv_lift is not None)
                        and (control_adv_lift >= baseline_adv_lift)
                    ),
                },
                {
                    "name": "ood_lift_stable_or_improved",
                    "control_ood_lift": control_ood_lift,
                    "baseline_ood_lift": baseline_ood_lift,
                    "operator": ">=",
                    "pass": bool(control_ood_lift >= baseline_ood_lift),
                },
                {
                    "name": "darbar_invocation_rate_efficiency",
                    "value": darbar_invocation_rate,
                    "threshold": args.max_darbar_invocation_rate,
                    "operator": "<=",
                    "pass": bool(
                        (darbar_invocation_rate is not None)
                        and (float(darbar_invocation_rate) <= float(args.max_darbar_invocation_rate))
                    ),
                },
            ]
        )
    else:
        checks.extend(
            [
                {
                    "name": "darbar_reduces_error_high_u",
                    "value": darbar,
                    "pass": None,
                    "applicable": False,
                },
                {
                    "name": "core_lift_within_tolerance",
                    "control_core_lift": control_core_lift,
                    "baseline_core_lift": baseline_core_lift,
                    "operator": ">=",
                    "pass": None,
                    "applicable": False,
                },
                {
                    "name": "adversarial_lift_stable_or_improved",
                    "control_adv_lift": control_adv_lift,
                    "baseline_adv_lift": baseline_adv_lift,
                    "operator": ">=",
                    "pass": None,
                    "applicable": False,
                },
                {
                    "name": "ood_lift_stable_or_improved",
                    "control_ood_lift": control_ood_lift,
                    "baseline_ood_lift": baseline_ood_lift,
                    "operator": ">=",
                    "pass": None,
                    "applicable": False,
                },
                {
                    "name": "darbar_invocation_rate_efficiency",
                    "value": darbar_invocation_rate,
                    "operator": "<=",
                    "pass": None,
                    "applicable": False,
                },
            ]
        )

    applicable_checks = [c for c in checks if c.get("applicable", True)]
    overall = all(bool(c.get("pass")) for c in applicable_checks)
    out = {
        "overall_pass": bool(overall),
        "stage": args.stage,
        "uncertainty_scope": args.uncertainty_scope,
        "checks": checks,
        "artifacts": {
            "reliability_json": args.reliability_json,
            "uncertainty_json": args.uncertainty_json,
            "control_phase2_json": args.control_phase2_json,
            "baseline_phase2_json": args.baseline_phase2_json,
        },
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")
    print(f"Milestone 3 PASS: {overall}")
    for c in checks:
        applicable = c.get("applicable", True)
        if not applicable:
            status = "SKIP"
        else:
            status = "PASS" if bool(c.get("pass")) else "FAIL"
        print(f"- {c['name']}: {status}")


if __name__ == "__main__":
    main()
