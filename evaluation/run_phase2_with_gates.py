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
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.create_split_manifest import build_split_manifest
from evaluation.evaluate_phase2_gates import evaluate_gates, write_markdown
from evaluation.run_phase2_robustness import (
    Phase2Runner,
    _load_uncertainty_thresholds_from_analysis,
    configure_phase2_env,
    load_split_selection,
)

def assert_ollama_available() -> None:
    try:
        import requests
    except Exception as exc:  # pragma: no cover - environment/setup issue
        raise RuntimeError("Ollama unavailable. Abort experiment.") from exc

    endpoint = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/api/tags"
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        payload = response.json()
        required_model = os.getenv("USER_MODEL")
        if required_model:
            available = {
                str(model.get("name", "")).strip()
                for model in (payload.get("models", []) if isinstance(payload, dict) else [])
            }
            if required_model not in available:
                raise RuntimeError(f"Required model missing: {required_model}")
    except Exception as exc:
        raise RuntimeError("Ollama unavailable. Abort experiment.") from exc


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
        "--gating-model",
        default=None,
        help="Optional trained gating model (.pt) to enable parametric minister weighting.",
    )
    parser.add_argument(
        "--uncertainty-thresholds-json",
        default=None,
        help="Optional uncertainty analysis JSON providing percentile-based control thresholds.",
    )
    parser.add_argument(
        "--uncertainty-thresholds-profile",
        choices=["all", "core", "ood", "adv"],
        default="all",
        help="Threshold profile key from uncertainty analysis.",
    )
    parser.add_argument("--uncertainty-threshold-1", type=float, default=None)
    parser.add_argument("--uncertainty-threshold-2", type=float, default=None)
    parser.add_argument("--uncertainty-threshold-3", type=float, default=None)
    parser.add_argument("--uncertainty-w-entropy", type=float, default=None)
    parser.add_argument("--uncertainty-w-confidence-variance", type=float, default=None)
    parser.add_argument("--uncertainty-w-kis-variance", type=float, default=None)
    parser.add_argument("--uncertainty-w-inverse-margin", type=float, default=None)
    parser.add_argument("--uncertainty-w-ml-prior-variance", type=float, default=None)
    parser.add_argument(
        "--enable-uncertainty-control",
        action="store_true",
        help="Compatibility flag: uncertainty control is enabled in Phase2 runs.",
    )
    parser.add_argument(
        "--uncertainty-model",
        default=None,
        help="Optional frozen learned uncertainty model artifact JSON.",
    )
    parser.add_argument(
        "--uncertainty-threshold-mode",
        choices=["runtime_percentile", "static"],
        default="runtime_percentile",
        help=(
            "Thresholding mode for uncertainty control. runtime_percentile runs a "
            "probe pass and uses runtime percentiles."
        ),
    )
    parser.add_argument(
        "--uncertainty-runtime-percentile-darbar",
        type=float,
        default=90.0,
        help="Percentile for DARBAR trigger in runtime_percentile mode.",
    )
    parser.add_argument(
        "--uncertainty-runtime-percentile-caution",
        type=float,
        default=75.0,
        help="Percentile for deeper-deliberation trigger in runtime_percentile mode.",
    )
    parser.add_argument(
        "--uncertainty-runtime-percentile-flag",
        type=float,
        default=None,
        help="Percentile for LOW_CERTAINTY flag in runtime_percentile mode.",
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
    parser.add_argument("--core-lift-threshold", type=float, default=0.0792)
    parser.add_argument("--ood-lift-threshold", type=float, default=0.02)
    parser.add_argument("--effect-size-threshold", type=float, default=0.7)
    parser.add_argument("--calibration-tolerance", type=float, default=0.02)
    parser.add_argument(
        "--max-mean-minister-weight-threshold",
        type=float,
        default=0.85,
    )
    parser.add_argument(
        "--max-runtime-hours",
        type=float,
        default=None,
        help="Optional hard runtime cap for the Phase2 process.",
    )
    parser.add_argument(
        "--lock-file",
        default="evaluation/results/phase2_robustness.lock",
        help="Singleton lock file for the underlying Phase2 run.",
    )
    parser.add_argument(
        "--disable-run-lock",
        action="store_true",
        help="Disable singleton lock (not recommended).",
    )
    parser.add_argument(
        "--force-clear-lock",
        action="store_true",
        help="Force-clear stale lock file before run.",
    )
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
    parser.add_argument(
        "--semantic-scorer",
        action="store_true",
        help="Use semantic principle matching scorer (EVAL_PRINCIPLE_MATCH_MODE=semantic).",
    )
    parser.add_argument(
        "--kis2-enabled",
        action="store_true",
        help="Enable KIS 2.0 embedding retrieval in parallel with KIS 1.0.",
    )
    parser.add_argument(
        "--kis2-principles-path",
        default="knowledge/principles.json",
        help="KIS2 principle catalog JSON path.",
    )
    parser.add_argument(
        "--kis2-embeddings-path",
        default="knowledge/embeddings.npy",
        help="KIS2 principle embedding index (.npy).",
    )
    parser.add_argument(
        "--kis2-embed-model",
        default="nomic-embed-text:latest",
        help="Embedding model name for KIS2 retrieval.",
    )
    parser.add_argument(
        "--kis2-top-k",
        type=int,
        default=5,
        help="Top-k retrieved principles for KIS2 prompt injection.",
    )
    parser.add_argument(
        "--kis2-reranker-json",
        default=None,
        help="Optional KIS2 reranker artifact JSON.",
    )
    parser.add_argument(
        "--kis2-activation-mode",
        choices=["always", "uncertainty_percentile"],
        default="uncertainty_percentile",
        help="KIS2 activation policy. Recommended: uncertainty_percentile.",
    )
    parser.add_argument(
        "--kis2-uncertainty-percentile",
        type=float,
        default=50.0,
        help="Percentile of runtime U used as KIS2 activation threshold.",
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
    if args.semantic_scorer:
        os.environ["EVAL_PRINCIPLE_MATCH_MODE"] = "semantic"
        enforced_env["EVAL_PRINCIPLE_MATCH_MODE"] = "semantic"
    for key, value in enforced_env.items():
        print(f"[ENV] {key}={value}")
    assert_ollama_available()

    run_core = True
    run_stress = not args.skip_stress
    run_ablations = args.include_ablations
    if args.core_only:
        run_stress = False

    if args.uncertainty_thresholds_json and args.uncertainty_threshold_mode == "static":
        loaded_thresholds = _load_uncertainty_thresholds_from_analysis(
            args.uncertainty_thresholds_json,
            profile=args.uncertainty_thresholds_profile,
        )
        if args.uncertainty_threshold_1 is None and "threshold_1" in loaded_thresholds:
            args.uncertainty_threshold_1 = loaded_thresholds["threshold_1"]
        if args.uncertainty_threshold_2 is None and "threshold_2" in loaded_thresholds:
            args.uncertainty_threshold_2 = loaded_thresholds["threshold_2"]
        if args.uncertainty_threshold_3 is None and "threshold_3" in loaded_thresholds:
            args.uncertainty_threshold_3 = loaded_thresholds["threshold_3"]
        print(
            f"[UNCERTAINTY] Loaded profile '{args.uncertainty_thresholds_profile}' "
            f"from {args.uncertainty_thresholds_json}: "
            f"t1={args.uncertainty_threshold_1} "
            f"t2={args.uncertainty_threshold_2} "
            f"t3={args.uncertainty_threshold_3}"
        )
    elif args.uncertainty_thresholds_json and args.uncertainty_threshold_mode == "runtime_percentile":
        print(
            f"[UNCERTAINTY] Ignoring --uncertainty-thresholds-json in runtime_percentile mode: "
            f"{args.uncertainty_thresholds_json}"
        )

    runner = Phase2Runner(
        split_dataset_ids=split_dataset_ids,
        split_name=args.split_name,
        diversity_prompts=args.diversity_prompts,
        max_runtime_seconds=(args.max_runtime_hours * 3600.0) if args.max_runtime_hours else None,
        gating_model_path=args.gating_model,
        lock_file=args.lock_file,
        disable_run_lock=args.disable_run_lock,
        force_clear_lock=args.force_clear_lock,
        uncertainty_threshold_1=args.uncertainty_threshold_1,
        uncertainty_threshold_2=args.uncertainty_threshold_2,
        uncertainty_threshold_3=args.uncertainty_threshold_3,
        uncertainty_w_entropy=args.uncertainty_w_entropy,
        uncertainty_w_confidence_variance=args.uncertainty_w_confidence_variance,
        uncertainty_w_kis_variance=args.uncertainty_w_kis_variance,
        uncertainty_w_inverse_margin=args.uncertainty_w_inverse_margin,
        uncertainty_w_ml_prior_variance=args.uncertainty_w_ml_prior_variance,
        uncertainty_model_path=args.uncertainty_model,
        uncertainty_threshold_mode=args.uncertainty_threshold_mode,
        uncertainty_runtime_percentile_darbar=args.uncertainty_runtime_percentile_darbar,
        uncertainty_runtime_percentile_caution=args.uncertainty_runtime_percentile_caution,
        uncertainty_runtime_percentile_flag=args.uncertainty_runtime_percentile_flag,
        kis2_enabled=args.kis2_enabled,
        kis2_principles_path=args.kis2_principles_path,
        kis2_embeddings_path=args.kis2_embeddings_path,
        kis2_embed_model=args.kis2_embed_model,
        kis2_top_k=args.kis2_top_k,
        kis2_reranker_json=args.kis2_reranker_json,
        kis2_activation_mode=args.kis2_activation_mode,
        kis2_uncertainty_percentile=args.kis2_uncertainty_percentile,
    )
    try:
        runner.run(
            scenario_limit=args.limit,
            run_core=run_core,
            run_stress=run_stress,
            run_ablations=run_ablations,
            only_ablation=None,
        )
    except TimeoutError as exc:
        print(f"[TIMEOUT] {exc}")
        return 124

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
        ood_lift_threshold=args.ood_lift_threshold,
        effect_size_threshold=args.effect_size_threshold,
        calibration_tolerance=args.calibration_tolerance,
        max_mean_minister_weight_threshold=args.max_mean_minister_weight_threshold,
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
