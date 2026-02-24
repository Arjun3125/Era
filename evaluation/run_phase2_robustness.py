#!/usr/bin/env python
"""
Phase 2 - Robustness & Attribution

Runs:
- Core benchmark (baseline vs council)
- Stress benchmarks (adversarial, out_of_distribution)
- Full ablation matrix (core dataset)

Outputs:
- evaluation/results/phase2_robustness_results.json
- evaluation/results/PHASE2_ROBUSTNESS_REPORT.md
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.evaluation_runner import EvaluationRunner
from evaluation.metrics.evaluation_metrics import EvaluationMetrics
from persona.modes.mode_orchestrator import ModeOrchestrator, ExecutionConfig
from persona.ollama_runtime import OllamaRuntime
from run_benchmark import BenchmarkRunner

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def configure_phase2_env() -> Dict[str, str]:
    """
    Enforce canonical evaluation runtime flags for Phase 2 runs.
    """
    canonical_env = {
        "USER_MODEL": "deepseek-r1:8b",
        "EVAL_NUM_PREDICT": "256",
        "EVAL_THINK_OFF": "1",
        "OLLAMA_HOST": "http://127.0.0.1:11434",
    }
    for key, value in canonical_env.items():
        os.environ[key] = value
    return canonical_env


def load_split_selection(split_manifest_path: str, split_name: str) -> Dict[str, set[str]]:
    """
    Load split manifest and return dataset->scenario-id-set for the selected split.

    Expected manifest shape:
    {
      "splits": {
        "train": {"core": [...], "adversarial": [...], "ood": [...], "all": [...]},
        "val": {...},
        "test": {...}
      }
    }
    """
    path = Path(split_manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Split manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    splits = data.get("splits", {})
    if split_name not in splits:
        raise ValueError(
            f"Split '{split_name}' not found in manifest. Available: {sorted(splits.keys())}"
        )
    selected = splits[split_name]
    dataset_map: Dict[str, set[str]] = {}
    for dataset_name, ids in selected.items():
        dataset_map[dataset_name] = set(ids or [])
    return dataset_map


class Phase2Runner:
    ABLATIONS = [
        "no_ministers",
        "no_kis_weighting",
        "no_ml_prior",
        "no_pwm",
        "no_mode_escalation",
    ]

    def __init__(
        self,
        split_dataset_ids: Optional[Dict[str, set[str]]] = None,
        split_name: Optional[str] = None,
        diversity_prompts: bool = False,
    ):
        self.eval_runner = EvaluationRunner()
        self.bench = BenchmarkRunner()
        self.mode_orchestrator = ModeOrchestrator(config=ExecutionConfig())
        self._extraction_debug_logged = False
        self._phase2_host_probe_logged = False
        self.split_dataset_ids = split_dataset_ids or {}
        self.split_name = split_name
        self.diversity_prompts = bool(diversity_prompts)
        self.results: Dict = {
            "metadata": {
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "model": "deepseek-r1:8b",
                "isolation_mode": True,
                "phase": "phase2_robustness_attribution",
                "split_name": self.split_name,
                "diversity_prompts": self.diversity_prompts,
            }
        }

    def _scenario_ids_for_dataset(self, dataset: str) -> Optional[list[str]]:
        """
        Optional split-aware scenario-id allowlist for the target dataset.
        """
        if not self.split_dataset_ids:
            return None
        ids = self.split_dataset_ids.get(dataset)
        if ids is None:
            ids = self.split_dataset_ids.get("all")
        if not ids:
            return None
        return sorted(ids)

    def _run_core(self, scenario_limit: int | None = None) -> tuple[Dict, Dict, Dict]:
        logger.info("[CORE] Core benchmark")
        core_baseline = self.eval_runner.run_evaluation(
            decision_engine=self.baseline_engine,
            run_name="phase2_core_baseline",
            scenario_limit=scenario_limit,
            dataset="core",
            scenario_ids=self._scenario_ids_for_dataset("core"),
        )
        core_council = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self.council_engine(s, ablation=None),
            run_name="phase2_core_council",
            scenario_limit=scenario_limit,
            dataset="core",
            scenario_ids=self._scenario_ids_for_dataset("core"),
        )
        core_cmp = self._compare_runs(core_baseline, core_council)
        return core_baseline, core_council, core_cmp

    def _run_stress(self, core_cmp: Dict, scenario_limit: int | None = None) -> Dict:
        logger.info("[STRESS] Stress benchmark (adversarial + ood)")
        adv_baseline = self.eval_runner.run_evaluation(
            decision_engine=self.baseline_engine,
            run_name="phase2_adversarial_baseline",
            scenario_limit=scenario_limit,
            dataset="adversarial",
            scenario_ids=self._scenario_ids_for_dataset("adversarial"),
        )
        adv_council = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self.council_engine(s, ablation=None),
            run_name="phase2_adversarial_council",
            scenario_limit=scenario_limit,
            dataset="adversarial",
            scenario_ids=self._scenario_ids_for_dataset("adversarial"),
        )
        adv_cmp = self._compare_runs(adv_baseline, adv_council)

        ood_baseline = self.eval_runner.run_evaluation(
            decision_engine=self.baseline_engine,
            run_name="phase2_ood_baseline",
            scenario_limit=scenario_limit,
            dataset="ood",
            scenario_ids=self._scenario_ids_for_dataset("ood"),
        )
        ood_council = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self.council_engine(s, ablation=None),
            run_name="phase2_ood_council",
            scenario_limit=scenario_limit,
            dataset="ood",
            scenario_ids=self._scenario_ids_for_dataset("ood"),
        )
        ood_cmp = self._compare_runs(ood_baseline, ood_council)

        stress = {
            "core": core_cmp,
            "adversarial": adv_cmp,
            "ood": ood_cmp,
            "delta_vs_core": {
                "adversarial": {
                    "lift_delta": adv_cmp["mean_difference"] - core_cmp["mean_difference"],
                    "calibration_delta_ece": adv_cmp["ece"] - core_cmp["ece"],
                    "calibration_delta_ece_raw": adv_cmp["ece_raw"] - core_cmp["ece_raw"],
                    "effect_size_delta": adv_cmp["cohens_d"] - core_cmp["cohens_d"],
                },
                "ood": {
                    "lift_delta": ood_cmp["mean_difference"] - core_cmp["mean_difference"],
                    "calibration_delta_ece": ood_cmp["ece"] - core_cmp["ece"],
                    "calibration_delta_ece_raw": ood_cmp["ece_raw"] - core_cmp["ece_raw"],
                    "effect_size_delta": ood_cmp["cohens_d"] - core_cmp["cohens_d"],
                },
            },
        }
        raw_runs = {
            "adversarial_baseline": adv_baseline,
            "adversarial_council": adv_council,
            "ood_baseline": ood_baseline,
            "ood_council": ood_council,
        }
        return {"stress": stress, "raw_runs": raw_runs}

    def _run_ablations(
        self,
        core_council: Dict,
        scenario_limit: int | None = None,
        only_ablation: str | None = None,
    ) -> Dict:
        logger.info("[ABLATIONS] Structural ablation matrix on core")
        ablation_list = [only_ablation] if only_ablation else self.ABLATIONS
        ablations = {}
        for ab in ablation_list:
            logger.info(f"  - Running ablation: {ab}")
            ablated = self.eval_runner.run_evaluation(
                decision_engine=lambda s, ablation=ab: self.council_engine(s, ablation=ablation),
                run_name=f"phase2_{ab}",
                scenario_limit=scenario_limit,
                dataset="core",
                scenario_ids=self._scenario_ids_for_dataset("core"),
            )
            ablations[ab] = self._ablation_delta(core_council, ablated)
        return ablations

    def _parse(self, response: str, fallback: str, acceptable_paths: list[str]) -> Tuple[str, float]:
        return self.bench._parse_model_response(response, fallback, acceptable_paths)

    def baseline_engine(self, scenario: Dict) -> Tuple[str, str, float]:
        return self.bench.baseline_decision_engine(scenario)

    def council_engine(self, scenario: Dict, ablation: str | None = None) -> Tuple[str, str, float]:
        self._apply_ablation(ablation)
        plan = self.mode_orchestrator.get_execution_plan("meeting")
        if not plan["use_dynamic_council"]:
            return self.baseline_engine(scenario)

        acceptable_paths = scenario.get("ground_truth_rubric", {}).get("acceptable_paths", [])
        fallback = "council_decision" if not ablation else f"{ablation}_decision"
        prompt = self._build_council_prompt(scenario, acceptable_paths)

        try:
            if not self._phase2_host_probe_logged:
                try:
                    import requests
                    status = requests.get("http://127.0.0.1:11434/api/tags", timeout=5).status_code
                    print("PHASE2_HOST_PROBE_STATUS:", status)
                except Exception as probe_error:
                    print("PHASE2_HOST_PROBE_ERROR:", probe_error)
                self._phase2_host_probe_logged = True
            llm = OllamaRuntime()
            response = llm.speak(
                "You are a decision system used for controlled benchmarking.",
                prompt,
            )
        except Exception:
            response = "DECISION: fallback_path\nRATIONALE: runtime failure\nCONFIDENCE: 0.00"

        decision_path, confidence = self._parse(response, fallback, acceptable_paths)
        if not self._extraction_debug_logged:
            assistant_text = response if response else ""
            print("EXTRACTED_TEXT_PREVIEW:", assistant_text[:200])
            print("DECISION_PATH_FOUND:", decision_path)
            print("CONFIDENCE_PARSED:", confidence)
            self._extraction_debug_logged = True
        return decision_path, response if response else "No response", confidence

    def _build_council_prompt(self, scenario: Dict, acceptable_paths: list[str]) -> str:
        scenario_text = scenario.get("input", "No input")[:220]
        if not self.diversity_prompts:
            return f"""As a decision council, analyze this scenario.

Scenario: {scenario_text}
Acceptable decision paths (choose exactly one): {acceptable_paths}
Consider risk, optionality, information value, and timing.

Provide your final answer in exactly this format:
DECISION: [choose one of the acceptable paths]
RATIONALE: [concise rationale]
CONFIDENCE: [0.00 to 1.00]"""

        return f"""As a diverse decision council, analyze this scenario.

Scenario: {scenario_text}
Acceptable decision paths (choose exactly one): {acceptable_paths}

Run four independent minister lenses before finalizing:
1) Minister Risk: minimize downside and irreversible harm.
2) Minister Optionality: preserve reversibility and information gain.
3) Minister Execution: optimize feasibility, timing, and implementation risk.
4) Minister Adversary: assume strategic opposition and compliance failure modes.

Hard diversity rule:
- Do not collapse early to one narrative.
- Surface at least one dissenting path unless all alternatives are clearly dominated.

Output format (exact keys, one line each):
MINISTER_RISK: [path] | [0.00-1.00] | [short reason]
MINISTER_OPTIONALITY: [path] | [0.00-1.00] | [short reason]
MINISTER_EXECUTION: [path] | [0.00-1.00] | [short reason]
MINISTER_ADVERSARY: [path] | [0.00-1.00] | [short reason]
DECISION: [choose one of the acceptable paths]
RATIONALE: [concise synthesis including dissent]
CONFIDENCE: [0.00 to 1.00]"""

    def _apply_ablation(self, ablation: str | None) -> None:
        self.mode_orchestrator.set_ablation_config(
            disable_ministers=ablation == "no_ministers",
            disable_kis=ablation == "no_kis_weighting",
            disable_ml_prior=ablation == "no_ml_prior",
            disable_pwm=ablation == "no_pwm",
            disable_mode_escalation=ablation == "no_mode_escalation",
        )

    def _compare_runs(self, baseline_results: Dict, council_results: Dict) -> Dict:
        baseline_map = baseline_results.get("scenario_scores_mean", {})
        council_map = council_results.get("scenario_scores_mean", {})
        shared_ids = sorted(set(baseline_map.keys()) & set(council_map.keys()))

        baseline_scores = [baseline_map[sid] for sid in shared_ids]
        council_scores = [council_map[sid] for sid in shared_ids]

        m = EvaluationMetrics(
            scenario_scores_baseline=baseline_scores,
            scenario_scores_council=council_scores,
        )
        ttest = m.compute_paired_ttest()
        effect = m.compute_effect_size()

        conf_map = council_results.get("scenario_confidence_mean", {})
        out_map = council_results.get("scenario_outcome_binary", {})
        cal_ids = sorted(set(conf_map.keys()) & set(out_map.keys()))
        pred = [float(conf_map[sid]) for sid in cal_ids]
        actual = [int(out_map[sid]) for sid in cal_ids]
        ece_raw = m.compute_ece(pred, actual)
        brier_raw = m.compute_brier(pred, actual)
        isotonic = m.apply_isotonic_regression_crossfit(
            pred, actual, n_folds=5, random_seed=42
        )
        calibrated_pred = isotonic["calibrated_probabilities"]
        ece_cal = m.compute_ece(calibrated_pred, actual)
        brier_cal = m.compute_brier(calibrated_pred, actual)

        return {
            "n_scenarios": len(shared_ids),
            "baseline_mean": m.compute_mean(baseline_scores),
            "council_mean": m.compute_mean(council_scores),
            "mean_difference": m.compute_mean(council_scores) - m.compute_mean(baseline_scores),
            "t_statistic": ttest["t_statistic"],
            "p_value": ttest["p_value"],
            "cohens_d": effect,
            # Parity with canonical v1.1: report calibrated metrics as primary.
            "ece": ece_cal,
            "brier": brier_cal,
            # Keep raw values visible for diagnostics.
            "ece_raw": ece_raw,
            "brier_raw": brier_raw,
            "isotonic_regression": {
                "method": "pair_adjacent_violators_crossfit",
                "crossfit_folds": isotonic["folds"],
                "expected_calibration_error": ece_cal,
                "brier_score": brier_cal,
                "ece_improvement": ece_raw - ece_cal,
                "brier_improvement": brier_raw - brier_cal,
                "model": isotonic["global_model"],
            },
        }

    def _ablation_delta(self, reference: Dict, ablated: Dict) -> Dict:
        ref_map = reference.get("scenario_scores_mean", {})
        abl_map = ablated.get("scenario_scores_mean", {})
        shared = sorted(set(ref_map.keys()) & set(abl_map.keys()))
        ref_scores = [ref_map[sid] for sid in shared]
        abl_scores = [abl_map[sid] for sid in shared]
        m = EvaluationMetrics(scenario_scores_baseline=ref_scores, scenario_scores_council=abl_scores)
        ttest = m.compute_paired_ttest()
        return {
            "n_scenarios": len(shared),
            "reference_mean": m.compute_mean(ref_scores),
            "ablated_mean": m.compute_mean(abl_scores),
            "performance_delta": m.compute_mean(ref_scores) - m.compute_mean(abl_scores),
            "percent_decrease": ((m.compute_mean(ref_scores) - m.compute_mean(abl_scores)) / m.compute_mean(ref_scores) * 100.0) if m.compute_mean(ref_scores) > 0 else 0.0,
            "effect_size_delta": m.compute_effect_size(),
            "t_statistic": ttest["t_statistic"],
            "p_value": ttest["p_value"],
        }

    def run(
        self,
        scenario_limit: int | None = None,
        run_core: bool = True,
        run_stress: bool = True,
        run_ablations: bool = True,
        only_ablation: str | None = None,
    ):
        logger.info("=== PHASE 2: ROBUSTNESS & ATTRIBUTION ===")
        if run_stress and not run_core:
            raise ValueError("Stress run requires core comparison metrics. Enable run_core.")

        raw_runs: Dict = self.results.get("raw_runs", {})
        core_council = None
        core_cmp = None

        if run_core:
            core_baseline, core_council, core_cmp = self._run_core(scenario_limit=scenario_limit)
            self.results["core"] = core_cmp
            raw_runs["core_baseline"] = core_baseline
            raw_runs["core_council"] = core_council

        if run_ablations and core_council is None:
            logger.info("[CORE-REF] Building core council reference for ablations")
            core_council = self.eval_runner.run_evaluation(
                decision_engine=lambda s: self.council_engine(s, ablation=None),
                run_name="phase2_core_council_reference",
                scenario_limit=scenario_limit,
                dataset="core",
                scenario_ids=self._scenario_ids_for_dataset("core"),
            )
            raw_runs["core_council_reference"] = core_council

        if run_stress and core_cmp is not None:
            stress_payload = self._run_stress(core_cmp=core_cmp, scenario_limit=scenario_limit)
            self.results["stress"] = stress_payload["stress"]
            raw_runs.update(stress_payload["raw_runs"])

        if run_ablations:
            self.results["ablations"] = self._run_ablations(
                core_council=core_council,
                scenario_limit=scenario_limit,
                only_ablation=only_ablation,
            )

        self.results["raw_runs"] = raw_runs

        self._save()
        self._write_report()
        logger.info("=== PHASE 2 COMPLETE ===")

    def _save(self):
        out = Path("evaluation/results/phase2_robustness_results.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.results, indent=2), encoding="utf-8")
        logger.info(f"Saved: {out}")

    def _write_report(self):
        out = Path("evaluation/results/PHASE2_ROBUSTNESS_REPORT.md")
        core = self.results.get("core")
        stress = self.results.get("stress")
        ab = self.results.get("ablations", {})
        lines = [
            "# ERA Phase 2 - Robustness & Attribution",
            "",
            f"- Timestamp (UTC): {self.results['metadata']['timestamp_utc']}",
            f"- Model: {self.results['metadata']['model']}",
            "",
        ]
        if core:
            lines.extend(
                [
                    "## Core",
                    f"- Lift: {core['mean_difference']:.6f}",
                    f"- Effect size (d): {core['cohens_d']:.6f}",
                    f"- ECE (Isotonic): {core['ece']:.6f}",
                    f"- ECE (Raw): {core['ece_raw']:.6f}",
                    f"- Brier (Isotonic): {core['brier']:.6f}",
                    f"- Brier (Raw): {core['brier_raw']:.6f}",
                    f"- ECE improvement: {core['isotonic_regression']['ece_improvement']:.6f}",
                    f"- Brier improvement: {core['isotonic_regression']['brier_improvement']:.6f}",
                    "",
                ]
            )
        if stress:
            lines.extend(
                [
                    "## Stress Deltas vs Core",
                    f"- Adversarial lift delta: {stress['delta_vs_core']['adversarial']['lift_delta']:.6f}",
                    f"- Adversarial calibration delta (ECE, isotonic): {stress['delta_vs_core']['adversarial']['calibration_delta_ece']:.6f}",
                    f"- Adversarial calibration delta (ECE, raw): {stress['delta_vs_core']['adversarial']['calibration_delta_ece_raw']:.6f}",
                    f"- Adversarial effect size delta: {stress['delta_vs_core']['adversarial']['effect_size_delta']:.6f}",
                    f"- OOD lift delta: {stress['delta_vs_core']['ood']['lift_delta']:.6f}",
                    f"- OOD calibration delta (ECE, isotonic): {stress['delta_vs_core']['ood']['calibration_delta_ece']:.6f}",
                    f"- OOD calibration delta (ECE, raw): {stress['delta_vs_core']['ood']['calibration_delta_ece_raw']:.6f}",
                    f"- OOD effect size delta: {stress['delta_vs_core']['ood']['effect_size_delta']:.6f}",
                    "",
                ]
            )
        lines.append("## Ablation Matrix (Core)")
        for k, v in ab.items():
            lines.append(
                f"- {k}: delta={v['performance_delta']:.6f}, percent_drop={v['percent_decrease']:.2f}%, d_delta={v['effect_size_delta']:.6f}"
            )
        if not ab:
            lines.append("- Not run in this execution.")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"Saved: {out}")


def main():
    parser = argparse.ArgumentParser(description="Phase 2 robustness runner")
    parser.add_argument("--limit", type=int, default=None, help="Optional scenario limit per dataset")
    parser.add_argument("--core-only", action="store_true", help="Run only core benchmark")
    parser.add_argument("--skip-stress", action="store_true", help="Skip stress datasets")
    parser.add_argument("--skip-ablations", action="store_true", help="Skip ablation matrix")
    parser.add_argument(
        "--diversity-prompts",
        action="store_true",
        help="Inject explicit multi-minister diversity instructions in council prompt.",
    )
    parser.add_argument(
        "--split-manifest",
        default=None,
        help="Optional path to split manifest JSON generated by create_split_manifest.py",
    )
    parser.add_argument(
        "--split-name",
        choices=["train", "val", "test"],
        default=None,
        help="Optional split name when --split-manifest is provided.",
    )
    parser.add_argument(
        "--only-ablation",
        choices=Phase2Runner.ABLATIONS,
        default=None,
        help="Run exactly one ablation (core only, builds council reference automatically)",
    )
    args = parser.parse_args()

    if args.only_ablation and args.skip_ablations:
        raise ValueError("--only-ablation cannot be used with --skip-ablations.")

    enforced_env = configure_phase2_env()
    for key, value in enforced_env.items():
        logger.info(f"[ENV] {key}={value}")

    split_dataset_ids: Dict[str, set[str]] = {}
    split_name = args.split_name
    if args.split_manifest:
        if not split_name:
            raise ValueError("--split-name is required when --split-manifest is provided.")
        split_dataset_ids = load_split_selection(args.split_manifest, split_name)
        logger.info(
            "[SPLIT] Loaded split '%s' from %s", split_name, args.split_manifest
        )
        for ds in ("core", "adversarial", "ood", "all"):
            if ds in split_dataset_ids:
                logger.info("[SPLIT] %s scenarios: %d", ds, len(split_dataset_ids[ds]))

    run_core = True
    run_stress = not args.skip_stress
    run_ablations = not args.skip_ablations
    if args.core_only:
        run_stress = False
    if args.only_ablation:
        run_core = False
        run_stress = False
        run_ablations = True

    runner = Phase2Runner(
        split_dataset_ids=split_dataset_ids,
        split_name=split_name,
        diversity_prompts=args.diversity_prompts,
    )
    runner.run(
        scenario_limit=args.limit,
        run_core=run_core,
        run_stress=run_stress,
        run_ablations=run_ablations,
        only_ablation=args.only_ablation,
    )


if __name__ == "__main__":
    main()
