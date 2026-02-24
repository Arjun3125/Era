#!/usr/bin/env python
"""
One-shot runner for split-scoped Phase2 evaluation + gate checks.

Flow:
1) Ensure split manifest exists (optional auto-create)
2) Run Phase2 robustness on selected split
3) Evaluate gate criteria and write reports
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.create_split_manifest import build_split_manifest
from evaluation.evaluate_phase2_gates import evaluate_gates, write_markdown
from evaluation.run_phase2_robustness import (
    Phase2Runner,
    configure_phase2_env,
    load_split_selection,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase2 + gate checks in one command")
    parser.add_argument(
        "--split-manifest",
        default="evaluation/benchmark_dataset/split_manifest_seed42.json",
        help="Split manifest path",
    )
    parser.add_argument(
        "--split-name",
        choices=["train", "val", "test"],
        default="test",
        help="Which split to evaluate",
    )
    parser.add_argument(
        "--create-split-if-missing",
        action="store_true",
        help="Create split manifest if not found",
    )
    parser.add_argument("--seed", type=int, default=42, help="Split seed (if creating)")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Validation split ratio")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test split ratio")
    parser.add_argument(
        "--benchmark-dir",
        default="evaluation/benchmark_dataset",
        help="Benchmark dataset directory",
    )

    parser.add_argument("--limit", type=int, default=None, help="Optional scenario limit per dataset")
    parser.add_argument("--core-only", action="store_true", help="Run only core benchmark")
    parser.add_argument("--skip-stress", action="store_true", help="Skip stress datasets")
    parser.add_argument(
        "--include-ablations",
        action="store_true",
        help="Also run ablations (default: false for clean gate checks)",
    )
    parser.add_argument(
        "--diversity-prompts",
        action="store_true",
        help="Inject explicit multi-minister diversity instructions in council prompt.",
    )

    parser.add_argument(
        "--candidate",
        default="evaluation/results/phase2_robustness_results.json",
        help="Candidate results JSON path",
    )
    parser.add_argument(
        "--baseline-reference",
        default=None,
        help="Optional baseline results JSON for relative no-collapse checks",
    )
    parser.add_argument("--core-lift-threshold", type=float, default=0.05)
    parser.add_argument("--effect-size-threshold", type=float, default=0.5)
    parser.add_argument("--calibration-tolerance", type=float, default=0.0)
    parser.add_argument(
        "--gate-report-json",
        default="evaluation/results/phase2_gate_report.json",
        help="Gate report JSON output path",
    )
    parser.add_argument(
        "--gate-report-md",
        default="evaluation/results/PHASE2_GATE_REPORT.md",
        help="Gate report markdown output path",
    )
    parser.add_argument(
        "--fail-on-revert",
        action="store_true",
        help="Return non-zero exit code when gate decision is REVERT",
    )
    args = parser.parse_args()

    split_manifest_path = Path(args.split_manifest)
    if not split_manifest_path.exists():
        if not args.create_split_if_missing:
            raise FileNotFoundError(
                f"Split manifest not found: {split_manifest_path}. "
                "Pass --create-split-if-missing to auto-create."
            )
        manifest = build_split_manifest(
            seed=args.seed,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            benchmark_dir=args.benchmark_dir,
        )
        split_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        split_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[SPLIT] Created: {split_manifest_path}")

    split_dataset_ids = load_split_selection(str(split_manifest_path), args.split_name)
    print(
        f"[SPLIT] Using split '{args.split_name}' "
        f"(core={len(split_dataset_ids.get('core', []))}, "
        f"adv={len(split_dataset_ids.get('adversarial', []))}, "
        f"ood={len(split_dataset_ids.get('ood', []))})"
    )

    enforced_env = configure_phase2_env()
    for key, value in enforced_env.items():
        print(f"[ENV] {key}={value}")

    run_core = True
    run_stress = not args.skip_stress
    run_ablations = args.include_ablations
    if args.core_only:
        run_stress = False

    runner = Phase2Runner(
        split_dataset_ids=split_dataset_ids,
        split_name=args.split_name,
        diversity_prompts=args.diversity_prompts,
    )
    runner.run(
        scenario_limit=args.limit,
        run_core=run_core,
        run_stress=run_stress,
        run_ablations=run_ablations,
        only_ablation=None,
    )

    candidate_path = Path(args.candidate)
    if not candidate_path.exists():
        raise FileNotFoundError(f"Candidate results missing: {candidate_path}")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    baseline_reference = None
    if args.baseline_reference:
        baseline_path = Path(args.baseline_reference)
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline reference missing: {baseline_path}")
        baseline_reference = json.loads(baseline_path.read_text(encoding="utf-8"))

    report = evaluate_gates(
        candidate,
        baseline_reference=baseline_reference,
        core_lift_threshold=args.core_lift_threshold,
        effect_size_threshold=args.effect_size_threshold,
        calibration_tolerance=args.calibration_tolerance,
    )

    report_json_path = Path(args.gate_report_json)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, args.gate_report_md)

    print(f"[GATES] Decision: {report['summary']['decision']}")
    if report["summary"]["failed_checks"]:
        print("[GATES] Failed checks:")
        for check in report["summary"]["failed_checks"]:
            print(f"  - {check}")

    if args.fail_on_revert and report["summary"]["decision"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
