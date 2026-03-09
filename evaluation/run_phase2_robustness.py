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
import copy
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.features.feature_extractor import get_feature_names
from evaluation.evaluation_runner import EvaluationRunner
from evaluation.adversarial_user_simulator import AdversarialUserSimulator
from evaluation.distribution_shift import SHIFT_MODES, apply_shift_mode, parse_shift_modes
from evaluation.gating_model import load_gating_bundle
from evaluation.gating_support import (
    MINISTER_ORDER,
    build_gating_features,
    build_model_input_from_spec,
    disagreement_entropy,
    irreversibility_score,
    minister_confidence_variance,
    parse_minister_outputs,
    vote_margin,
)
from evaluation.learned_uncertainty import LearnedUncertaintyPredictor
from evaluation.kis2_retrieval import KIS2Config, KIS2Retrieval
from evaluation.metrics.evaluation_metrics import EvaluationMetrics
from evaluation.scoring.outcome_scorer import OutcomeScorer
from evaluation.red_team_governance import (
    inject_governance_attack_text,
    summarize_governance_metrics,
)
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
        "EVAL_REQUEST_TIMEOUT_SECONDS": "120",
        "EVAL_FAIL_FAST_ERRORS": "1",
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


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {int(pid)}", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            out = (proc.stdout or "").strip().lower()
            if "no tasks are running" in out:
                return False
            return str(int(pid)) in out
        except Exception:
            return False
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def _safe_load_json(path: Path) -> Dict[str, Any]:
    """
    Best-effort JSON reader for lock metadata.

    Uses utf-8-sig to tolerate BOM-prefixed files (common on Windows tooling).
    On parse/read failure, returns a sentinel parse error key so callers can fail closed.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"_parse_error": str(exc)}


def _load_uncertainty_thresholds_from_analysis(
    analysis_path: str,
    *,
    profile: str = "all",
) -> Dict[str, float]:
    """
    Load control thresholds from uncertainty analysis artifact.

    Expected shape:
      {
        "control_thresholds": {
          "all": {"threshold_1": ..., "threshold_2": ..., "threshold_3": ...},
          "core": {...}, ...
        }
      }
    """
    data = _safe_load_json(Path(analysis_path))
    if data.get("_parse_error"):
        raise ValueError(f"Failed to parse uncertainty analysis JSON: {analysis_path}")
    block = (data.get("control_thresholds", {}) or {})
    selected = block.get(profile) or block.get("all") or {}
    out: Dict[str, float] = {}
    for key in ("threshold_1", "threshold_2", "threshold_3"):
        value = selected.get(key)
        if value is None:
            continue
        out[key] = float(value)
    return out


def _compute_percentile(values: list[float], percentile: float) -> float:
    """Linear-interpolated percentile for a list of numeric values."""
    if not values:
        return 0.0
    p = max(0.0, min(100.0, float(percentile)))
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (p / 100.0) * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return float(ordered[lo] + ((ordered[hi] - ordered[lo]) * frac))


def estimate_phase2_workload(
    *,
    run_core: bool,
    run_stress: bool,
    run_ablations: bool,
    only_ablation: str | None,
    scenario_limit: int | None,
    split_dataset_ids: Dict[str, set[str]],
    n_seeds: int,
    sec_per_call: float,
    adversarial_self_play_rounds: int = 0,
    adversarial_self_play_dataset: str = "core",
    shift_modes: Optional[List[str]] = None,
    shift_dataset: str = "core",
    governance_red_team: bool = False,
    governance_dataset: str = "core",
) -> Dict[str, Any]:
    if split_dataset_ids:
        core_count = len(split_dataset_ids.get("core", set()))
        adv_count = len(split_dataset_ids.get("adversarial", set()))
        ood_count = len(split_dataset_ids.get("ood", set()))
    else:
        core_count = EvaluationRunner.EXPECTED_CORE_TOTAL
        adv_count = EvaluationRunner.EXPECTED_ADVERSARIAL_TOTAL
        ood_count = EvaluationRunner.EXPECTED_OOD_TOTAL

    if scenario_limit is not None:
        core_count = min(core_count, scenario_limit)
        adv_count = min(adv_count, scenario_limit)
        ood_count = min(ood_count, scenario_limit)

    baseline_decisions = 0
    council_decisions = 0
    if run_core:
        baseline_decisions += core_count * n_seeds
        council_decisions += core_count * n_seeds
    if run_stress:
        baseline_decisions += (adv_count + ood_count) * n_seeds
        council_decisions += (adv_count + ood_count) * n_seeds

    if run_ablations:
        ab_count = 1 if only_ablation else len(Phase2Runner.ABLATIONS)
        if not run_core:
            council_decisions += core_count * n_seeds
        council_decisions += core_count * n_seeds * ab_count

    self_play_rounds = max(0, int(adversarial_self_play_rounds or 0))
    self_play_decisions = 0
    if self_play_rounds > 0:
        if str(adversarial_self_play_dataset).lower() == "adversarial":
            self_play_count = adv_count
        elif str(adversarial_self_play_dataset).lower() == "ood":
            self_play_count = ood_count
        else:
            self_play_count = core_count
        # K rounds + initial pass
        self_play_decisions = self_play_count * n_seeds * (self_play_rounds + 1)
        council_decisions += self_play_decisions

    shift_decisions = 0
    normalized_shift_modes = [m for m in (shift_modes or []) if m in SHIFT_MODES]
    if normalized_shift_modes:
        if str(shift_dataset).lower() == "adversarial":
            shift_count = adv_count
        elif str(shift_dataset).lower() == "ood":
            shift_count = ood_count
        else:
            shift_count = core_count
        shift_decisions = shift_count * n_seeds * len(normalized_shift_modes)
        council_decisions += shift_decisions

    governance_decisions = 0
    if bool(governance_red_team):
        if str(governance_dataset).lower() == "adversarial":
            gov_count = adv_count
        elif str(governance_dataset).lower() == "ood":
            gov_count = ood_count
        else:
            gov_count = core_count
        governance_decisions = gov_count * n_seeds
        council_decisions += governance_decisions

    llm_calls_low = baseline_decisions + council_decisions
    llm_calls_high = baseline_decisions + (2 * council_decisions)
    est_hours_low = (llm_calls_low * sec_per_call) / 3600.0
    est_hours_high = (llm_calls_high * sec_per_call) / 3600.0
    return {
        "core_scenarios": int(core_count),
        "adversarial_scenarios": int(adv_count),
        "ood_scenarios": int(ood_count),
        "n_seeds": int(n_seeds),
        "baseline_decisions": int(baseline_decisions),
        "council_decisions": int(council_decisions),
        "adversarial_self_play_decisions": int(self_play_decisions),
        "distribution_shift_decisions": int(shift_decisions),
        "governance_red_team_decisions": int(governance_decisions),
        "llm_calls_low": int(llm_calls_low),
        "llm_calls_high": int(llm_calls_high),
        "sec_per_call_assumed": float(sec_per_call),
        "estimated_hours_low": float(est_hours_low),
        "estimated_hours_high": float(est_hours_high),
        "recommended_max_runtime_hours": float(est_hours_high + 1.0),
    }


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
        max_runtime_seconds: float | None = None,
        gating_model_path: str | None = None,
        lock_file: str = "evaluation/results/phase2_robustness.lock",
        disable_run_lock: bool = False,
        force_clear_lock: bool = False,
        uncertainty_threshold_1: float | None = None,
        uncertainty_threshold_2: float | None = None,
        uncertainty_threshold_3: float | None = None,
        uncertainty_w_entropy: float | None = None,
        uncertainty_w_confidence_variance: float | None = None,
        uncertainty_w_kis_variance: float | None = None,
        uncertainty_w_inverse_margin: float | None = None,
        uncertainty_w_ml_prior_variance: float | None = None,
        uncertainty_model_path: str | None = None,
        uncertainty_threshold_mode: str = "runtime_percentile",
        uncertainty_runtime_percentile_darbar: float = 90.0,
        uncertainty_runtime_percentile_caution: float = 75.0,
        uncertainty_runtime_percentile_flag: float | None = None,
        adversarial_self_play_rounds: int = 0,
        adversarial_self_play_dataset: str = "core",
        adversarial_objectives: Optional[List[str]] = None,
        shift_modes: Optional[List[str]] = None,
        shift_dataset: str = "core",
        governance_red_team: bool = False,
        governance_dataset: str = "core",
        kis2_enabled: bool = False,
        kis2_principles_path: str = "knowledge/principles.json",
        kis2_embeddings_path: str = "knowledge/embeddings.npy",
        kis2_embed_model: str = "nomic-embed-text:latest",
        kis2_top_k: int = 5,
        kis2_reranker_json: str | None = None,
        kis2_activation_mode: str = "uncertainty_percentile",
        kis2_uncertainty_percentile: float = 50.0,
    ):
        self.eval_runner = EvaluationRunner()
        self.bench = BenchmarkRunner()
        self.mode_orchestrator = ModeOrchestrator(config=ExecutionConfig())
        self._extraction_debug_logged = False
        self._phase2_host_probe_logged = False
        self.split_dataset_ids = split_dataset_ids or {}
        self.split_name = split_name
        self.diversity_prompts = bool(diversity_prompts)
        self.max_runtime_seconds = (
            float(max_runtime_seconds)
            if max_runtime_seconds is not None and max_runtime_seconds > 0
            else None
        )
        self.lock_file = str(lock_file)
        self.disable_run_lock = bool(disable_run_lock)
        self.force_clear_lock = bool(force_clear_lock)
        self._lock_acquired = False
        self.gating_model_path = gating_model_path
        self.uncertainty_model_path = uncertainty_model_path
        self.uncertainty_threshold_mode = str(uncertainty_threshold_mode or "runtime_percentile")
        self.uncertainty_runtime_percentile_darbar = float(uncertainty_runtime_percentile_darbar)
        self.uncertainty_runtime_percentile_caution = float(uncertainty_runtime_percentile_caution)
        self.uncertainty_runtime_percentile_flag = float(
            uncertainty_runtime_percentile_flag
            if uncertainty_runtime_percentile_flag is not None
            else uncertainty_runtime_percentile_caution
        )
        self._gating_model = None
        self._gating_payload: Dict | None = None
        self._gating_feature_spec: Dict | None = None
        self._gating_weight_history: list[Dict[str, float]] = []
        self._uncertainty_policy_history: list[Dict[str, Any]] = []
        self._uncertainty_model: LearnedUncertaintyPredictor | None = None
        self._uncertainty_probe_mode = False
        self.adversarial_self_play_rounds = max(0, int(adversarial_self_play_rounds or 0))
        self.adversarial_self_play_dataset = str(adversarial_self_play_dataset or "core").strip().lower()
        self.adversarial_objectives = list(adversarial_objectives or [])
        self._adversarial_simulator: AdversarialUserSimulator | None = None
        if self.adversarial_self_play_rounds > 0:
            self._adversarial_simulator = AdversarialUserSimulator(
                objectives=self.adversarial_objectives or None
            )
        self.shift_modes = [m for m in (shift_modes or []) if m in SHIFT_MODES]
        self.shift_dataset = str(shift_dataset or "core").strip().lower()
        self.governance_red_team = bool(governance_red_team)
        self.governance_dataset = str(governance_dataset or "core").strip().lower()
        self.kis2_enabled = bool(kis2_enabled)
        self.kis2_principles_path = str(kis2_principles_path)
        self.kis2_embeddings_path = str(kis2_embeddings_path)
        self.kis2_embed_model = str(kis2_embed_model or "nomic-embed-text:latest")
        self.kis2_top_k = max(1, int(kis2_top_k or 5))
        self.kis2_reranker_json = str(kis2_reranker_json) if kis2_reranker_json else None
        self.kis2_activation_mode = str(kis2_activation_mode or "uncertainty_percentile").strip().lower()
        if self.kis2_activation_mode not in {"always", "uncertainty_percentile"}:
            raise ValueError(
                f"Unsupported kis2_activation_mode='{self.kis2_activation_mode}'. "
                "Use one of: always, uncertainty_percentile."
            )
        self.kis2_uncertainty_percentile = float(kis2_uncertainty_percentile)
        self._kis2_uncertainty_threshold: float = 0.5
        self._kis2_retrieval: KIS2Retrieval | None = None
        self._kis2_history: list[Dict[str, Any]] = []
        if self.kis2_enabled:
            self._kis2_retrieval = KIS2Retrieval(
                KIS2Config(
                    enabled=True,
                    principles_path=self.kis2_principles_path,
                    embeddings_path=self.kis2_embeddings_path,
                    embed_model=self.kis2_embed_model,
                    top_k=self.kis2_top_k,
                    reranker_json=self.kis2_reranker_json,
                    auto_build_embeddings=True,
                )
            )
        self._gating_minister_order: list[str] = list(MINISTER_ORDER)
        policy = self.mode_orchestrator.uncertainty_policy
        if uncertainty_threshold_1 is not None:
            policy.threshold_1 = float(uncertainty_threshold_1)
        if uncertainty_threshold_2 is not None:
            policy.threshold_2 = float(uncertainty_threshold_2)
        if uncertainty_threshold_3 is not None:
            policy.threshold_3 = float(uncertainty_threshold_3)
        if uncertainty_w_entropy is not None:
            policy.w_entropy = float(uncertainty_w_entropy)
        if uncertainty_w_confidence_variance is not None:
            policy.w_confidence_variance = float(uncertainty_w_confidence_variance)
        if uncertainty_w_kis_variance is not None:
            policy.w_kis_variance = float(uncertainty_w_kis_variance)
        if uncertainty_w_inverse_margin is not None:
            policy.w_inverse_margin = float(uncertainty_w_inverse_margin)
        if uncertainty_w_ml_prior_variance is not None:
            policy.w_ml_prior_variance = float(uncertainty_w_ml_prior_variance)
        if self.uncertainty_model_path:
            self._uncertainty_model = LearnedUncertaintyPredictor.from_json(
                self.uncertainty_model_path
            )
            self.mode_orchestrator.set_uncertainty_predictor(
                self._uncertainty_model.predict,
                metadata=self._uncertainty_model.metadata(),
            )
            # Static model thresholds are optional; runtime-percentile mode overrides them.
            if self.uncertainty_threshold_mode != "runtime_percentile":
                threshold_cfg = self._uncertainty_model.threshold_config()
                if uncertainty_threshold_1 is None and threshold_cfg.get("threshold_1") is not None:
                    policy.threshold_1 = float(threshold_cfg["threshold_1"])
                if uncertainty_threshold_2 is None and threshold_cfg.get("threshold_2") is not None:
                    policy.threshold_2 = float(threshold_cfg["threshold_2"])
                if uncertainty_threshold_3 is None and threshold_cfg.get("threshold_3") is not None:
                    policy.threshold_3 = float(threshold_cfg["threshold_3"])
        if self.gating_model_path:
            model, payload = load_gating_bundle(self.gating_model_path)
            self._gating_model = model
            self._gating_payload = payload
            self._gating_minister_order = list(payload.get("minister_order", MINISTER_ORDER))
            self._gating_feature_spec = dict(payload.get("feature_spec", {}) or {})
            self._gating_feature_spec.setdefault("input_dim", int(payload.get("input_dim", 50)))
        self._deadline_epoch: float | None = None
        self.results: Dict = {
            "metadata": {
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "model": "deepseek-r1:8b",
                "isolation_mode": True,
                "phase": "phase2_robustness_attribution",
                "split_name": self.split_name,
                "diversity_prompts": self.diversity_prompts,
                "max_runtime_seconds": self.max_runtime_seconds,
                "gating_model_path": self.gating_model_path,
                "uncertainty_model_path": self.uncertainty_model_path,
                "lock_file": self.lock_file,
                "run_lock_enabled": not self.disable_run_lock,
                "gating_enabled": bool(self._gating_model is not None),
                "uncertainty_control_enabled": True,
                "uncertainty_model_enabled": bool(self._uncertainty_model is not None),
                "uncertainty_threshold_mode": self.uncertainty_threshold_mode,
                "uncertainty_threshold_1": self.mode_orchestrator.uncertainty_policy.threshold_1,
                "uncertainty_threshold_2": self.mode_orchestrator.uncertainty_policy.threshold_2,
                "uncertainty_threshold_3": self.mode_orchestrator.uncertainty_policy.threshold_3,
                "uncertainty_w_entropy": self.mode_orchestrator.uncertainty_policy.w_entropy,
                "uncertainty_w_confidence_variance": self.mode_orchestrator.uncertainty_policy.w_confidence_variance,
                "uncertainty_w_kis_variance": self.mode_orchestrator.uncertainty_policy.w_kis_variance,
                "uncertainty_w_inverse_margin": self.mode_orchestrator.uncertainty_policy.w_inverse_margin,
                "uncertainty_w_ml_prior_variance": self.mode_orchestrator.uncertainty_policy.w_ml_prior_variance,
                "uncertainty_runtime_percentiles": {
                    "darbar": self.uncertainty_runtime_percentile_darbar,
                    "caution": self.uncertainty_runtime_percentile_caution,
                    "flag": self.uncertainty_runtime_percentile_flag,
                },
                "adversarial_self_play_rounds": self.adversarial_self_play_rounds,
                "adversarial_self_play_dataset": self.adversarial_self_play_dataset,
                "adversarial_objectives": list(self.adversarial_objectives),
                "shift_modes": list(self.shift_modes),
                "shift_dataset": self.shift_dataset,
                "governance_red_team": self.governance_red_team,
                "governance_dataset": self.governance_dataset,
                "kis2_enabled": self.kis2_enabled,
                "kis2_principles_path": self.kis2_principles_path,
                "kis2_embeddings_path": self.kis2_embeddings_path,
                "kis2_embed_model": self.kis2_embed_model,
                "kis2_top_k": self.kis2_top_k,
                "kis2_reranker_json": self.kis2_reranker_json,
                "kis2_activation_mode": self.kis2_activation_mode,
                "kis2_uncertainty_percentile": self.kis2_uncertainty_percentile,
                "kis2_uncertainty_threshold": self._kis2_uncertainty_threshold,
            }
        }
        if self._uncertainty_model is not None:
            self.results["metadata"]["uncertainty_model_metadata"] = self._uncertainty_model.metadata()
        if self._kis2_retrieval is not None:
            self.results["metadata"]["kis2_metadata"] = self._kis2_retrieval.metadata()

    def _probe_runtime_uncertainty_thresholds(
        self,
        *,
        scenario_limit: int | None,
        run_core: bool,
        run_stress: bool,
    ) -> None:
        """
        Pass 1/2: run council decisions with escalation disabled and collect U distribution.
        Then set thresholds from runtime percentiles for pass 2.
        """
        if not (run_core or run_stress):
            logger.info(
                "[UNCERTAINTY] Runtime percentile mode requested but no core/stress run; "
                "skipping probe pass."
            )
            return

        logger.info(
            "[UNCERTAINTY] Pass 1/2 probe: collecting runtime U distribution "
            "(escalation disabled)"
        )
        self._uncertainty_policy_history = []
        self._uncertainty_probe_mode = True
        try:
            if run_core:
                self._check_runtime("uncertainty_probe_core")
                self.eval_runner.run_evaluation(
                    decision_engine=lambda s: self.council_engine(s, ablation=None),
                    run_name="phase2_core_council_uncertainty_probe",
                    scenario_limit=scenario_limit,
                    dataset="core",
                    scenario_ids=self._scenario_ids_for_dataset("core"),
                    deadline_epoch=self._deadline_epoch,
                    split_name=self.split_name,
                )
            if run_stress:
                self._check_runtime("uncertainty_probe_adversarial")
                self.eval_runner.run_evaluation(
                    decision_engine=lambda s: self.council_engine(s, ablation=None),
                    run_name="phase2_adversarial_council_uncertainty_probe",
                    scenario_limit=scenario_limit,
                    dataset="adversarial",
                    scenario_ids=self._scenario_ids_for_dataset("adversarial"),
                    deadline_epoch=self._deadline_epoch,
                    split_name=self.split_name,
                )
                self._check_runtime("uncertainty_probe_ood")
                self.eval_runner.run_evaluation(
                    decision_engine=lambda s: self.council_engine(s, ablation=None),
                    run_name="phase2_ood_council_uncertainty_probe",
                    scenario_limit=scenario_limit,
                    dataset="ood",
                    scenario_ids=self._scenario_ids_for_dataset("ood"),
                    deadline_epoch=self._deadline_epoch,
                    split_name=self.split_name,
                )
        finally:
            self._uncertainty_probe_mode = False

        u_values = [
            float(item.get("u", 0.0))
            for item in self._uncertainty_policy_history
            if item.get("u") is not None
        ]
        if not u_values:
            raise RuntimeError(
                "Runtime percentile thresholding requested, but probe pass produced no uncertainty values."
            )
        threshold_1 = _compute_percentile(u_values, self.uncertainty_runtime_percentile_darbar)
        threshold_2 = _compute_percentile(u_values, self.uncertainty_runtime_percentile_caution)
        threshold_3 = _compute_percentile(u_values, self.uncertainty_runtime_percentile_flag)
        policy = self.mode_orchestrator.uncertainty_policy
        policy.threshold_1 = float(threshold_1)
        policy.threshold_2 = float(threshold_2)
        policy.threshold_3 = float(threshold_3)
        self.results["metadata"]["uncertainty_threshold_1"] = float(threshold_1)
        self.results["metadata"]["uncertainty_threshold_2"] = float(threshold_2)
        self.results["metadata"]["uncertainty_threshold_3"] = float(threshold_3)
        self.results["metadata"]["uncertainty_threshold_source"] = "runtime_percentile_probe"
        self.results["metadata"]["uncertainty_runtime_probe"] = {
            "n_observations": len(u_values),
            "u_min": float(min(u_values)),
            "u_max": float(max(u_values)),
            "u_mean": float(sum(u_values) / max(len(u_values), 1)),
            "percentiles": {
                "darbar": self.uncertainty_runtime_percentile_darbar,
                "caution": self.uncertainty_runtime_percentile_caution,
                "flag": self.uncertainty_runtime_percentile_flag,
            },
            "thresholds": {
                "threshold_1": float(threshold_1),
                "threshold_2": float(threshold_2),
                "threshold_3": float(threshold_3),
            },
        }
        if self._kis2_retrieval is not None and self.kis2_activation_mode == "uncertainty_percentile":
            kis2_threshold = _compute_percentile(u_values, self.kis2_uncertainty_percentile)
            self._kis2_uncertainty_threshold = float(kis2_threshold)
            self.results["metadata"]["kis2_uncertainty_threshold"] = float(kis2_threshold)
            self.results["metadata"]["kis2_uncertainty_threshold_source"] = "runtime_percentile_probe"
            logger.info(
                "[KIS2] Uncertainty-gated activation threshold: %.6f (P%.1f)",
                kis2_threshold,
                self.kis2_uncertainty_percentile,
            )
        logger.info(
            "[UNCERTAINTY] Probe thresholds: t1=%.6f (P%.1f), t2=%.6f (P%.1f), t3=%.6f (P%.1f)",
            threshold_1,
            self.uncertainty_runtime_percentile_darbar,
            threshold_2,
            self.uncertainty_runtime_percentile_caution,
            threshold_3,
            self.uncertainty_runtime_percentile_flag,
        )
        # Reset history so final summaries reflect pass-2 (actual control) only.
        self._uncertainty_policy_history = []

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

    def _check_runtime(self, stage: str) -> None:
        if self._deadline_epoch is None:
            return
        remaining = self._deadline_epoch - time.time()
        if remaining <= 0:
            raise TimeoutError(f"Phase2 max runtime exceeded before stage '{stage}'")

    def _acquire_run_lock(self) -> None:
        if self.disable_run_lock:
            return
        lock_path = Path(self.lock_file)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        current_pid = int(os.getpid())
        payload = {
            "pid": current_pid,
            "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "split_name": self.split_name,
        }

        if self.force_clear_lock and lock_path.exists():
            try:
                lock_path.unlink()
            except Exception as exc:
                raise RuntimeError(f"Failed to clear lock file: {lock_path} ({exc})") from exc

        for _ in range(2):
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2)
                self._lock_acquired = True
                return
            except FileExistsError:
                existing = _safe_load_json(lock_path)
                if existing.get("_parse_error"):
                    raise RuntimeError(
                        f"Lock file exists but is unreadable ({lock_path}). "
                        "Treating as active to avoid concurrent runs. "
                        "Use --force-clear-lock only if you verified no run is active."
                    )
                existing_pid = int(existing.get("pid", 0) or 0)
                if existing_pid and _pid_is_alive(existing_pid):
                    started = existing.get("started_utc", "unknown")
                    raise RuntimeError(
                        f"Another Phase2 run is active (pid={existing_pid}, started={started}). "
                        f"Lock file: {lock_path}. Stop it first or use --force-clear-lock if stale."
                    )
                try:
                    lock_path.unlink()
                except Exception as exc:
                    raise RuntimeError(
                        f"Lock exists but could not be removed: {lock_path} ({exc})"
                    ) from exc
        raise RuntimeError(f"Could not acquire Phase2 lock: {lock_path}")

    def _release_run_lock(self) -> None:
        if self.disable_run_lock or not self._lock_acquired:
            return
        lock_path = Path(self.lock_file)
        current_pid = int(os.getpid())
        try:
            if lock_path.exists():
                existing = _safe_load_json(lock_path)
                existing_pid = int(existing.get("pid", 0) or 0)
                if existing_pid in (0, current_pid):
                    lock_path.unlink()
        finally:
            self._lock_acquired = False

    @staticmethod
    def _completion_checks(
        *,
        run_core: bool,
        run_stress: bool,
        run_ablations: bool,
        raw_runs: Dict[str, Any],
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        expected_raw = []
        if run_core:
            expected_raw.extend(["core_baseline", "core_council"])
        if run_stress:
            expected_raw.extend(
                ["adversarial_baseline", "adversarial_council", "ood_baseline", "ood_council"]
            )
        missing_raw = [k for k in expected_raw if k not in raw_runs]
        confidence_records_total = 0
        for payload in raw_runs.values():
            confidence_records_total += len((payload or {}).get("confidence_records", []) or [])
        return {
            "expected_raw_runs": expected_raw,
            "missing_raw_runs": missing_raw,
            "has_core_section": bool(run_core and "core" in results),
            "has_stress_section": bool((not run_stress) or ("stress" in results)),
            "has_ablations_section": bool((not run_ablations) or ("ablations" in results)),
            "confidence_records_total": int(confidence_records_total),
            "complete": bool(
                (len(missing_raw) == 0)
                and ((not run_core) or ("core" in results))
                and ((not run_stress) or ("stress" in results))
                and ((not run_ablations) or ("ablations" in results))
            ),
        }

    def _speak_with_num_predict(
        self,
        *,
        system_context: str,
        prompt: str,
        num_predict_override: int | None = None,
    ) -> str:
        previous = os.environ.get("EVAL_NUM_PREDICT")
        try:
            if num_predict_override is not None:
                os.environ["EVAL_NUM_PREDICT"] = str(int(num_predict_override))
            llm = OllamaRuntime()
            return llm.speak(system_context, prompt)
        finally:
            if previous is None:
                os.environ.pop("EVAL_NUM_PREDICT", None)
            else:
                os.environ["EVAL_NUM_PREDICT"] = previous

    @staticmethod
    def _uncertainty_signals_from_ministers(
        scenario: Dict[str, Any],
        minister_outputs: Dict,
        *,
        response_text: str | None = None,
    ) -> Dict[str, float | None]:
        def _extract_named_value(name: str) -> float | None:
            pattern = rf"(?im)^\s*{re.escape(name)}\s*[:=]\s*([0-9]*\.?[0-9]+)\s*$"
            match = re.search(pattern, response_text or "")
            if not match:
                return None
            try:
                return float(match.group(1))
            except Exception:
                return None

        kis_var = _extract_named_value("KIS_VARIANCE")
        ml_prior_var = _extract_named_value("ML_PRIOR_VARIANCE")
        irr_score = float(irreversibility_score(scenario))
        if not minister_outputs:
            return {
                "minister_vote_entropy": None,
                "disagreement_entropy": None,
                "entropy_conditional": None,
                "minister_confidence_variance": None,
                "minister_mean_confidence": None,
                "confidence": None,
                "vote_concentration_index": None,
                "decision_margin": None,
                "inverse_margin": None,
                "irreversibility_score": irr_score,
                "kis_variance": kis_var,
                "ml_prior_variance": ml_prior_var,
            }
        confidences = [float(out.confidence) for out in minister_outputs.values()]
        conf_mean = sum(confidences) / max(len(confidences), 1)
        vote_counts: Dict[str, int] = {}
        for out in minister_outputs.values():
            vote_counts[out.path] = vote_counts.get(out.path, 0) + 1
        top_votes = max(vote_counts.values()) if vote_counts else 0
        vote_concentration = float(top_votes / max(len(minister_outputs), 1))
        d_margin = float(vote_margin(minister_outputs))
        d_entropy = float(disagreement_entropy(minister_outputs))
        return {
            "minister_vote_entropy": d_entropy,
            "disagreement_entropy": d_entropy,
            # Offline learned uncertainty used entropy_conditional = entropy * historical_error_prior.
            # Runtime proxy keeps this feature on the same numeric scale to avoid distribution shift.
            "entropy_conditional": float(max(0.0, min(1.0, d_entropy * 0.25))),
            "minister_confidence_variance": float(minister_confidence_variance(minister_outputs)),
            "minister_mean_confidence": float(max(0.0, min(1.0, conf_mean))),
            "confidence": float(max(0.0, min(1.0, conf_mean))),
            "vote_concentration_index": float(max(0.0, min(1.0, vote_concentration))),
            "decision_margin": d_margin,
            "inverse_margin": float(max(0.0, min(1.0, 1.0 - d_margin))),
            "irreversibility_score": irr_score,
            "kis_variance": kis_var,
            "ml_prior_variance": ml_prior_var,
        }

    def _run_core(self, scenario_limit: int | None = None) -> tuple[Dict, Dict, Dict]:
        logger.info("[CORE] Core benchmark")
        core_baseline = self.eval_runner.run_evaluation(
            decision_engine=self.baseline_engine,
            run_name="phase2_core_baseline",
            scenario_limit=scenario_limit,
            dataset="core",
            scenario_ids=self._scenario_ids_for_dataset("core"),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
        )
        core_council = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self.council_engine(s, ablation=None),
            run_name="phase2_core_council",
            scenario_limit=scenario_limit,
            dataset="core",
            scenario_ids=self._scenario_ids_for_dataset("core"),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
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
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
        )
        adv_council = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self.council_engine(s, ablation=None),
            run_name="phase2_adversarial_council",
            scenario_limit=scenario_limit,
            dataset="adversarial",
            scenario_ids=self._scenario_ids_for_dataset("adversarial"),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
        )
        adv_cmp = self._compare_runs(adv_baseline, adv_council)

        ood_baseline = self.eval_runner.run_evaluation(
            decision_engine=self.baseline_engine,
            run_name="phase2_ood_baseline",
            scenario_limit=scenario_limit,
            dataset="ood",
            scenario_ids=self._scenario_ids_for_dataset("ood"),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
        )
        ood_council = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self.council_engine(s, ablation=None),
            run_name="phase2_ood_council",
            scenario_limit=scenario_limit,
            dataset="ood",
            scenario_ids=self._scenario_ids_for_dataset("ood"),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
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

    def _council_engine_with_self_play(
        self,
        scenario: Dict[str, Any],
        *,
        rounds: int,
        ablation: str | None = None,
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        """
        Sequential adversarial self-play wrapper around council_engine.

        Round 0 runs the original scenario; rounds 1..K run adversarially mutated
        follow-ups produced by AdversarialUserSimulator.
        """
        if rounds <= 0 or self._adversarial_simulator is None:
            return self.council_engine(scenario, ablation=ablation)

        seed = os.getenv("EVAL_SEED", "0")
        scenario_id = str(scenario.get("_scenario_id", "unknown"))
        base_scenario = copy.deepcopy(scenario)
        current_scenario = copy.deepcopy(scenario)
        scorer = OutcomeScorer()
        round_rows: list[Dict[str, Any]] = []
        attack_trace: list[Dict[str, Any]] = []

        final_decision_path = ""
        final_rationale = ""
        final_confidence = 0.0
        final_metadata: Dict[str, Any] = {}

        for round_idx in range(0, rounds + 1):
            decision_path, rationale, confidence, metadata = self.council_engine(
                current_scenario,
                ablation=ablation,
            )
            final_decision_path = str(decision_path)
            final_rationale = str(rationale)
            final_confidence = float(confidence)
            final_metadata = dict(metadata or {})

            rubric = base_scenario.get("ground_truth_rubric", {}) or {}
            evaluation = scorer.evaluate_decision(
                scenario_id=scenario_id,
                category=str(base_scenario.get("category", "")),
                decision_path=final_decision_path,
                decision_rationale=final_rationale,
                ground_truth_rubric=rubric,
            )
            round_rows.append(
                {
                    "round_index": int(round_idx),
                    "score": float(evaluation.score),
                    "success": bool(evaluation.success),
                    "decision_path": final_decision_path,
                    "confidence": float(final_confidence),
                    "mode": str((final_metadata.get("control_policy") or {}).get("target_mode", "meeting")),
                    "principles_satisfied_count": int(len(evaluation.principles_satisfied)),
                    "required_principles_count": int(len(rubric.get("principles_required", []) or [])),
                }
            )
            if round_idx >= rounds:
                break
            generated = self._adversarial_simulator.generate(
                current_scenario,
                system_output={
                    "decision_path": final_decision_path,
                    "rationale": final_rationale,
                    "confidence": final_confidence,
                },
                metadata={
                    "scenario_id": scenario_id,
                    "seed": seed,
                    "round_index": round_idx + 1,
                },
            )
            attack_trace.append(
                {
                    "round_index": int(round_idx + 1),
                    "objective": str(generated.objective),
                    "attack_type": str(generated.attack_type),
                    "instruction": str(generated.instruction),
                }
            )
            current_scenario = generated.scenario

        seq_summary = self._adversarial_simulator.summarize_rounds(round_rows)
        seq_summary["attack_trace"] = attack_trace
        seq_summary["scenario_id"] = scenario_id

        merged_metadata = dict(final_metadata or {})
        merged_metadata["adversarial_self_play"] = seq_summary
        return final_decision_path, final_rationale, final_confidence, merged_metadata

    @staticmethod
    def _summarize_adversarial_self_play(run_payload: Dict[str, Any]) -> Dict[str, Any]:
        records = list((run_payload or {}).get("confidence_records", []) or [])
        seq_rows = [
            rec.get("adversarial_self_play")
            for rec in records
            if isinstance(rec.get("adversarial_self_play"), dict)
        ]
        if not seq_rows:
            return {
                "n_decisions": 0,
                "adversarial_rounds": 0,
                "regret_increase_rate": 0.0,
                "contradiction_rate": 0.0,
                "principle_drop_rate": 0.0,
                "mode_instability": 0.0,
                "score_drop_curve": [],
                "score_curve": [],
            }

        n = len(seq_rows)
        rounds = int(max(item.get("adversarial_rounds", 0) for item in seq_rows))
        regret = [float(item.get("regret_increase_rate", 0.0)) for item in seq_rows]
        contradiction = [float(item.get("contradiction_rate", 0.0)) for item in seq_rows]
        principle_drop = [float(item.get("principle_drop_rate", 0.0)) for item in seq_rows]
        instability = [float(item.get("mode_instability", 0.0)) for item in seq_rows]

        def _curve_mean(key: str) -> list[float]:
            width = max(len(item.get(key, []) or []) for item in seq_rows)
            out: list[float] = []
            for idx in range(width):
                vals = [
                    float(item.get(key, [])[idx])
                    for item in seq_rows
                    if idx < len(item.get(key, []) or [])
                ]
                out.append(float(sum(vals) / max(len(vals), 1)))
            return out

        return {
            "n_decisions": int(n),
            "adversarial_rounds": int(rounds),
            "regret_increase_rate": float(sum(regret) / max(n, 1)),
            "contradiction_rate": float(sum(contradiction) / max(n, 1)),
            "principle_drop_rate": float(sum(principle_drop) / max(n, 1)),
            "mode_instability": float(sum(instability) / max(n, 1)),
            "score_drop_curve": _curve_mean("score_drop_curve"),
            "score_curve": _curve_mean("score_curve"),
        }

    def _run_adversarial_self_play(
        self,
        *,
        scenario_limit: int | None = None,
    ) -> Dict[str, Any]:
        if self._adversarial_simulator is None or self.adversarial_self_play_rounds <= 0:
            return {}
        dataset = self.adversarial_self_play_dataset
        if dataset not in {"core", "adversarial", "ood"}:
            raise ValueError(
                f"Invalid adversarial self-play dataset '{dataset}'. Use: core|adversarial|ood."
            )
        logger.info(
            "[M4][SELF-PLAY] Running %d-round adversarial self-play on dataset=%s",
            self.adversarial_self_play_rounds,
            dataset,
        )
        run_name = f"phase2_{dataset}_council_adversarial_selfplay"
        payload = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self._council_engine_with_self_play(
                s,
                rounds=self.adversarial_self_play_rounds,
                ablation=None,
            ),
            run_name=run_name,
            scenario_limit=scenario_limit,
            dataset=dataset,
            scenario_ids=self._scenario_ids_for_dataset(dataset),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
        )
        summary = self._summarize_adversarial_self_play(payload)
        return {
            "dataset": dataset,
            "rounds": int(self.adversarial_self_play_rounds),
            "objectives": list(self.adversarial_objectives or self._adversarial_simulator.objectives),
            "metrics": summary,
            "raw_run": payload,
        }

    def _council_engine_with_shift_mode(
        self,
        scenario: Dict[str, Any],
        *,
        shift_mode: str,
        ablation: str | None = None,
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        scenario_id = str(scenario.get("_scenario_id", "unknown"))
        seed = str(os.getenv("EVAL_SEED", "0"))
        shifted = apply_shift_mode(
            scenario,
            shift_mode=shift_mode,
            scenario_id=scenario_id,
            seed=seed,
        )
        decision_path, rationale, confidence, metadata = self.council_engine(
            shifted.scenario,
            ablation=ablation,
        )
        merged_meta = dict(metadata or {})
        merged_meta["distribution_shift"] = {
            "mode": shifted.shift_mode,
            "variant": shifted.shift_variant,
        }
        return decision_path, rationale, confidence, merged_meta

    @staticmethod
    def _summarize_distribution_shift_run(
        payload: Dict[str, Any],
        *,
        reference_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        stats = (payload or {}).get("aggregated_statistics", {}) or {}
        ref_stats = (reference_payload or {}).get("aggregated_statistics", {}) if reference_payload else {}
        records = list((payload or {}).get("confidence_records", []) or [])
        mean_score = float(stats.get("overall_mean", stats.get("mean", 0.0)))
        ref_mean = float((ref_stats or {}).get("overall_mean", (ref_stats or {}).get("mean", 0.0)))
        u_vals = []
        low_cert = 0
        darbar = 0
        # Simple deterministic ECE over 10 bins from confidence records.
        bins = [[] for _ in range(10)]
        for rec in records:
            u = rec.get("uncertainty_composite")
            try:
                if u is not None:
                    u_vals.append(float(u))
            except Exception:
                pass
            try:
                conf = float(rec.get("confidence", rec.get("predicted_confidence", 0.0)))
                correct = int(rec.get("correct", rec.get("outcome", 0)))
                idx = min(9, max(0, int(conf * 10)))
                bins[idx].append((conf, correct))
            except Exception:
                pass
            policy = rec.get("control_policy") or {}
            if str(rec.get("confidence_flag", "")).upper() == "LOW_CERTAINTY":
                low_cert += 1
            if bool(policy.get("switch_to_darbar")):
                darbar += 1
        ece = 0.0
        n = max(1, len(records))
        for bucket in bins:
            if not bucket:
                continue
            bucket_n = len(bucket)
            conf_mean = sum(x[0] for x in bucket) / bucket_n
            acc_mean = sum(x[1] for x in bucket) / bucket_n
            ece += (bucket_n / n) * abs(conf_mean - acc_mean)

        return {
            "n_decisions": int(len(records)),
            "mean_score": float(mean_score),
            "score_delta_vs_reference": float(mean_score - ref_mean),
            "ece": float(ece),
            "mean_u": float(sum(u_vals) / max(1, len(u_vals))) if u_vals else 0.0,
            "low_certainty_rate": float(low_cert / max(1, len(records))),
            "darbar_rate": float(darbar / max(1, len(records))),
        }

    def _run_distribution_shift_suite(
        self,
        *,
        scenario_limit: int | None = None,
        reference_run_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not self.shift_modes:
            return {}
        dataset = self.shift_dataset
        if dataset not in {"core", "adversarial", "ood"}:
            raise ValueError(f"Invalid shift dataset '{dataset}'. Use: core|adversarial|ood.")

        out: Dict[str, Any] = {"dataset": dataset, "modes": {}}
        for mode in self.shift_modes:
            logger.info("[M4][SHIFT] Running shift mode=%s dataset=%s", mode, dataset)
            run_name = f"phase2_{dataset}_council_shift_{mode}"
            payload = self.eval_runner.run_evaluation(
                decision_engine=lambda s, m=mode: self._council_engine_with_shift_mode(
                    s,
                    shift_mode=m,
                    ablation=None,
                ),
                run_name=run_name,
                scenario_limit=scenario_limit,
                dataset=dataset,
                scenario_ids=self._scenario_ids_for_dataset(dataset),
                deadline_epoch=self._deadline_epoch,
                split_name=self.split_name,
            )
            out["modes"][mode] = {
                "metrics": self._summarize_distribution_shift_run(
                    payload,
                    reference_payload=reference_run_payload,
                ),
                "raw_run": payload,
            }
        return out

    def _council_engine_with_governance_redteam(
        self,
        scenario: Dict[str, Any],
        *,
        ablation: str | None = None,
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        mutated = dict(scenario)
        mutated["input"] = inject_governance_attack_text(str(mutated.get("input", "") or ""))
        decision_path, rationale, confidence, metadata = self.council_engine(mutated, ablation=ablation)
        merged_meta = dict(metadata or {})
        merged_meta["governance_red_team"] = True
        return decision_path, rationale, confidence, merged_meta

    def _run_governance_red_team(
        self,
        *,
        scenario_limit: int | None = None,
        reference_run_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not self.governance_red_team:
            return {}
        dataset = self.governance_dataset
        if dataset not in {"core", "adversarial", "ood"}:
            raise ValueError(
                f"Invalid governance dataset '{dataset}'. Use: core|adversarial|ood."
            )
        logger.info("[M4][GOV] Running governance red-team dataset=%s", dataset)
        run_name = f"phase2_{dataset}_council_governance_redteam"
        payload = self.eval_runner.run_evaluation(
            decision_engine=lambda s: self._council_engine_with_governance_redteam(s, ablation=None),
            run_name=run_name,
            scenario_limit=scenario_limit,
            dataset=dataset,
            scenario_ids=self._scenario_ids_for_dataset(dataset),
            deadline_epoch=self._deadline_epoch,
            split_name=self.split_name,
        )
        metrics = summarize_governance_metrics(
            payload,
            reference_run_payload=reference_run_payload,
        )
        return {
            "dataset": dataset,
            "metrics": metrics,
            "raw_run": payload,
        }

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
                deadline_epoch=self._deadline_epoch,
                split_name=self.split_name,
            )
            ablations[ab] = self._ablation_delta(core_council, ablated)
        return ablations

    def _parse(self, response: str, fallback: str, acceptable_paths: list[str]) -> Tuple[str, float]:
        return self.bench._parse_model_response(response, fallback, acceptable_paths)

    def _parse_with_single_repair(
        self,
        *,
        response: str,
        fallback: str,
        acceptable_paths: list[str],
    ) -> Tuple[str, float, str, bool]:
        """
        Parse response in fail-fast mode with one bounded format-repair attempt.

        This preserves strict research behavior (no heuristic 0.5 fallback), while
        reducing run aborts from occasional formatting drift.
        """
        try:
            decision_path, confidence = self._parse(response, fallback, acceptable_paths)
            return decision_path, confidence, response, False
        except ValueError as exc:
            err = str(exc)
            acceptable_line = ", ".join(str(p) for p in acceptable_paths)
            repair_prompt = f"""Reformat the prior council output into exactly 3 lines.

Acceptable paths (choose exactly one): {acceptable_line}

Output format (exactly):
DECISION: <one acceptable path>
RATIONALE: <<= 20 words>
CONFIDENCE: <0.00 to 1.00>

Prior output:
{response}
"""
            repaired = self._speak_with_num_predict(
                system_context="You are a strict output formatter for benchmarking.",
                prompt=repair_prompt,
                num_predict_override=128,
            )
            decision_path, confidence = self._parse(repaired, fallback, acceptable_paths)
            merged = (
                f"{response}\n"
                f"FORMAT_REPAIR_USED: 1\n"
                f"FORMAT_REPAIR_TRIGGER: {err}\n"
                f"FORMAT_REPAIRED_OUTPUT:\n{repaired}"
            )
            return decision_path, confidence, merged, True

    def _choose_weighted_decision(
        self,
        *,
        scenario: Dict,
        acceptable_paths: list[str],
        minister_outputs: Dict,
        fallback_decision: str,
        fallback_confidence: float,
    ) -> Tuple[str, float, Dict[str, float]]:
        if not self._gating_model or not minister_outputs:
            return fallback_decision, fallback_confidence, {}

        import torch

        if self._gating_feature_spec:
            model_input, _ = build_model_input_from_spec(
                scenario,
                minister_outputs,
                self._gating_feature_spec,
            )
        else:
            _, model_input, _ = build_gating_features(scenario, minister_outputs)
        x = torch.tensor([model_input], dtype=torch.float32)
        with torch.no_grad():
            weights_tensor = self._gating_model(x).cpu().view(-1)
        minister_order = self._gating_minister_order
        if len(minister_order) != len(weights_tensor):
            minister_order = list(MINISTER_ORDER[: len(weights_tensor)])
        weight_by_minister = {
            minister_order[i]: float(weights_tensor[i].item())
            for i in range(len(weights_tensor))
        }
        self._gating_weight_history.append(weight_by_minister)

        acceptable_norm = {
            str(p).strip().lower().replace("-", "_").replace(" ", "_") for p in acceptable_paths
        }
        path_score: Dict[str, float] = {}
        path_weight: Dict[str, float] = {}
        for name, out in minister_outputs.items():
            if name not in weight_by_minister:
                continue
            path = str(out.path).strip().lower().replace("-", "_").replace(" ", "_")
            if acceptable_norm and path not in acceptable_norm:
                continue
            w = weight_by_minister[name]
            c = float(out.confidence)
            path_score[path] = path_score.get(path, 0.0) + (w * c)
            path_weight[path] = path_weight.get(path, 0.0) + w

        if not path_score:
            return fallback_decision, fallback_confidence, weight_by_minister

        chosen_path = max(path_score.items(), key=lambda item: item[1])[0]
        denom = max(path_weight.get(chosen_path, 1e-6), 1e-6)
        chosen_conf = max(0.0, min(1.0, path_score[chosen_path] / denom))
        return chosen_path, chosen_conf, weight_by_minister

    def _summarize_gating_weights(self) -> Dict:
        if not self._gating_weight_history:
            return {}
        ministers = sorted(self._gating_weight_history[0].keys())
        means = {}
        for m in ministers:
            vals = [row.get(m, 0.0) for row in self._gating_weight_history]
            means[m] = float(sum(vals) / len(vals))
        max_mean = max(means.values()) if means else 0.0
        return {
            "n_observations": len(self._gating_weight_history),
            "mean_weights": means,
            "max_mean_weight": float(max_mean),
        }

    def _summarize_uncertainty_policy(self) -> Dict[str, Any]:
        if not self._uncertainty_policy_history:
            return {}
        n = len(self._uncertainty_policy_history)
        u_vals = [float(item.get("u", 0.0)) for item in self._uncertainty_policy_history]
        darbar = sum(1 for item in self._uncertainty_policy_history if item.get("switch_to_darbar"))
        deeper = sum(
            1
            for item in self._uncertainty_policy_history
            if item.get("increase_deliberation_depth")
        )
        low_cert = sum(
            1
            for item in self._uncertainty_policy_history
            if str(item.get("confidence_flag", "")).upper() == "LOW_CERTAINTY"
        )
        second_pass = sum(
            1 for item in self._uncertainty_policy_history if item.get("second_pass_applied")
        )
        principle_enforced = sum(
            1
            for item in self._uncertainty_policy_history
            if ((item.get("principle_activation") or {}).get("enabled"))
        )
        kis2_triggered = sum(
            1 for item in self._uncertainty_policy_history if item.get("kis2_triggered")
        )
        return {
            "n_observations": n,
            "mean_u": float(sum(u_vals) / max(n, 1)),
            "darbar_rate": float(darbar / max(n, 1)),
            "deeper_deliberation_rate": float(deeper / max(n, 1)),
            "low_certainty_rate": float(low_cert / max(n, 1)),
            "second_pass_rate": float(second_pass / max(n, 1)),
            "principle_activation_rate": float(principle_enforced / max(n, 1)),
            "kis2_trigger_rate": float(kis2_triggered / max(n, 1)),
        }

    def _summarize_kis2_usage(self) -> Dict[str, Any]:
        if not self._kis2_history:
            return {}
        n = len(self._kis2_history)
        active = sum(1 for row in self._kis2_history if bool(row.get("enabled")))
        errors = sum(1 for row in self._kis2_history if row.get("error"))
        counts = [float(row.get("count", 0.0)) for row in self._kis2_history if row.get("enabled")]
        top_scores = [
            float(row.get("top_score", 0.0))
            for row in self._kis2_history
            if row.get("enabled") and ("top_score" in row)
        ]
        return {
            "n_observations": int(n),
            "activation_rate": float(active / max(n, 1)),
            "mean_retrieved_count": float(sum(counts) / max(len(counts), 1)),
            "mean_top_score": float(sum(top_scores) / max(len(top_scores), 1)),
            "error_rate": float(errors / max(n, 1)),
        }

    @staticmethod
    def _estimate_information_ambiguity(
        scenario: Dict[str, Any],
        *,
        base_features: list[float] | None = None,
    ) -> float:
        text = f"{scenario.get('input', '')} {scenario.get('context', '')}".lower()
        uncertainty_hits = sum(
            1
            for token in [
                "uncertain",
                "unknown",
                "unclear",
                "ambiguous",
                "missing",
                "limited data",
                "insufficient",
                "volatile",
            ]
            if token in text
        )
        text_ambiguity = max(0.0, min(1.0, uncertainty_hits / 4.0))

        feature_ambiguity = 0.0
        try:
            names = get_feature_names()
            if base_features and "information_completeness" in names:
                idx = names.index("information_completeness")
                if idx < len(base_features):
                    info_complete = float(base_features[idx])
                    feature_ambiguity = max(0.0, min(1.0, 1.0 - info_complete))
        except Exception:
            feature_ambiguity = 0.0

        return max(text_ambiguity, feature_ambiguity)

    def _detect_principle_activation(
        self,
        *,
        scenario: Dict[str, Any],
        minister_outputs: Dict,
        uncertainty_signals: Dict[str, Any],
        control_policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Rule-based domain trigger detector for KIS 2.0 principle-lens amplification.

        Uses existing feature extraction and uncertainty signals (no retrieval, no retraining).
        """
        base_features, _, _ = build_gating_features(scenario, minister_outputs)
        category = str(scenario.get("category", "")).strip().lower()
        irr = float(uncertainty_signals.get("irreversibility_score") or irreversibility_score(scenario))
        disagreement = float(uncertainty_signals.get("disagreement_entropy") or 0.0)
        u = float(control_policy.get("u", 0.0))
        info_ambiguity = self._estimate_information_ambiguity(scenario, base_features=base_features)
        long_horizon_signal = 1.0 if category == "long_horizon" else 0.0
        if long_horizon_signal == 0.0:
            text = f"{scenario.get('input', '')} {scenario.get('context', '')}".lower()
            if any(token in text for token in ["long-term", "long term", "years", "year", "decade"]):
                long_horizon_signal = 0.75

        domain_scores: Dict[str, float] = {
            "reversibility_downside": 0.0,
            "systems_feedback": 0.0,
            "temporal_optionality": 0.0,
            "information_value": 0.0,
        }
        reasons: Dict[str, list[str]] = {k: [] for k in domain_scores}

        if irr >= 0.67:
            domain_scores["reversibility_downside"] += irr
            reasons["reversibility_downside"].append(f"irreversibility={irr:.2f}")
        if disagreement >= 0.60:
            domain_scores["systems_feedback"] += disagreement
            reasons["systems_feedback"].append(f"disagreement_entropy={disagreement:.2f}")
        if long_horizon_signal >= 0.50:
            domain_scores["temporal_optionality"] += long_horizon_signal
            reasons["temporal_optionality"].append(f"long_horizon_signal={long_horizon_signal:.2f}")
        if info_ambiguity >= 0.45:
            domain_scores["information_value"] += info_ambiguity
            reasons["information_value"].append(f"information_ambiguity={info_ambiguity:.2f}")
        if u >= float(self.mode_orchestrator.uncertainty_policy.threshold_2):
            # High-U cases get explicit information/system checks.
            domain_scores["information_value"] += 0.25
            reasons["information_value"].append(f"high_u={u:.2f}")
            domain_scores["systems_feedback"] += 0.15
            reasons["systems_feedback"].append(f"high_u={u:.2f}")

        domain_to_principles = {
            "reversibility_downside": ["reversibility", "downside_asymmetry"],
            "systems_feedback": ["systemic_barriers", "feedback_loops"],
            "temporal_optionality": ["time_value", "optionality"],
            "information_value": ["information_value"],
        }

        ranked_domains = sorted(
            [(k, float(v)) for k, v in domain_scores.items() if float(v) > 0.0],
            key=lambda item: item[1],
            reverse=True,
        )
        top_domains = ranked_domains[:3]
        principles: list[str] = []
        for name, _ in top_domains:
            for p in domain_to_principles.get(name, []):
                if p not in principles:
                    principles.append(p)

        return {
            "enabled": bool(principles),
            "uncertainty_u": float(u),
            "top_domains": [{"name": n, "score": s, "reasons": reasons.get(n, [])} for n, s in top_domains],
            "principles": principles,
            "feature_vector_dim": len(base_features),
            "signals": {
                "irreversibility_score": irr,
                "disagreement_entropy": disagreement,
                "long_horizon_signal": long_horizon_signal,
                "information_ambiguity": info_ambiguity,
            },
        }

    @staticmethod
    def _build_principle_activation_block(principle_activation: Dict[str, Any] | None) -> str:
        if not principle_activation or not principle_activation.get("enabled"):
            return ""
        principles = list(principle_activation.get("principles", []) or [])
        domains = [d.get("name") for d in (principle_activation.get("top_domains", []) or []) if d.get("name")]
        principle_checks = {
            "reversibility": "- Evaluate reversibility implications before commitment.",
            "downside_asymmetry": "- Evaluate downside asymmetry and worst-case containment.",
            "systemic_barriers": "- Evaluate systemic barriers and structural constraints.",
            "feedback_loops": "- Evaluate feedback-loop and second-order consequences.",
            "time_value": "- Evaluate time-value impact of delaying vs acting now.",
            "optionality": "- Evaluate optionality preservation under uncertainty.",
            "information_value": "- Evaluate information value: what new signal changes the decision?",
        }
        checks = [principle_checks[p] for p in principles if p in principle_checks]
        if not checks:
            return ""
        checks_blob = "\n".join(checks)
        return f"""
Mandatory principle coverage pass (internal; keep final output format unchanged):
- Activated domains: {domains}
- Before finalizing decision, explicitly run these checks:
{checks_blob}
- If any check materially changes the top choice, update DECISION and explain tradeoff in RATIONALE.
"""

    def _build_kis2_context(
        self,
        *,
        scenario: Dict[str, Any],
        uncertainty_signals: Dict[str, Any] | None = None,
        principle_activation: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        if self._kis2_retrieval is None:
            return None
        signals = uncertainty_signals or {}
        pa = principle_activation or {}
        activated_domains = [
            str(item.get("name"))
            for item in (pa.get("top_domains", []) or [])
            if item.get("name")
        ]
        activated_principles = [str(x) for x in (pa.get("principles", []) or [])]
        try:
            retrieval = self._kis2_retrieval.retrieve(
                scenario=scenario,
                irreversibility=float(
                    signals.get("irreversibility_score", irreversibility_score(scenario))
                ),
                disagreement_entropy=float(signals.get("disagreement_entropy", 0.0)),
                activated_domains=activated_domains,
                activated_principles=activated_principles,
                top_k=self.kis2_top_k,
            )
            self._kis2_history.append(
                {
                    "enabled": True,
                    "count": int(len(retrieval.get("retrieved", []) or [])),
                    "top_score": float(
                        (retrieval.get("retrieved", [{}])[0] or {}).get("final_score", 0.0)
                    ),
                }
            )
            return retrieval
        except Exception as exc:
            self._kis2_history.append(
                {
                    "enabled": False,
                    "count": 0,
                    "error": str(exc),
                }
            )
            return {
                "enabled": False,
                "error": str(exc),
                "retrieved": [],
                "principles": [],
            }

    def _kis2_should_activate(self, *, control_policy: Dict[str, Any] | None) -> bool:
        if self._kis2_retrieval is None:
            return False
        if self.kis2_activation_mode == "always":
            return True
        # uncertainty_percentile mode
        u = float((control_policy or {}).get("u", 0.0))
        return bool(u >= float(self._kis2_uncertainty_threshold))

    def baseline_engine(self, scenario: Dict) -> Tuple[str, str, float]:
        return self.bench.baseline_decision_engine(scenario)

    def council_engine(self, scenario: Dict, ablation: str | None = None) -> Tuple[str, str, float, Dict[str, Any]]:
        self._apply_ablation(ablation)
        plan = self.mode_orchestrator.get_execution_plan("meeting")
        if not plan["use_dynamic_council"]:
            return self.baseline_engine(scenario)

        acceptable_paths = scenario.get("ground_truth_rubric", {}).get("acceptable_paths", [])
        fallback = "council_decision" if not ablation else f"{ablation}_decision"
        base_mode = "meeting"
        kis2_context = None
        if self._kis2_retrieval is not None and self.kis2_activation_mode == "always":
            kis2_context = self._build_kis2_context(scenario=scenario)
        prompt = self._build_council_prompt(
            scenario,
            acceptable_paths,
            mode=base_mode,
            kis2_retrieval=kis2_context,
        )

        if not self._phase2_host_probe_logged:
            import requests

            status = requests.get("http://127.0.0.1:11434/api/tags", timeout=5).status_code
            print("PHASE2_HOST_PROBE_STATUS:", status)
            self._phase2_host_probe_logged = True

        response = self._speak_with_num_predict(
            system_context="You are a decision system used for controlled benchmarking.",
            prompt=prompt,
        )
        minister_outputs = parse_minister_outputs(response)
        uncertainty_signals = self._uncertainty_signals_from_ministers(
            scenario,
            minister_outputs,
            response_text=response,
        )
        control_policy = self.mode_orchestrator.apply_uncertainty_control(
            signals=uncertainty_signals,
            base_mode=base_mode,
        )
        if self._uncertainty_probe_mode:
            control_policy["target_mode"] = base_mode
            control_policy["switch_to_darbar"] = False
            control_policy["increase_deliberation_depth"] = False
            control_policy["extra_minister_round"] = False
            control_policy["enable_memory_recall"] = False
            control_policy["confidence_flag"] = "NORMAL"
            control_policy["num_predict_override"] = None
            control_policy["probe_pass"] = True

        kis2_triggered = self._kis2_should_activate(control_policy=control_policy)
        if self._uncertainty_probe_mode:
            kis2_triggered = False
        should_escalate = bool(
            control_policy["switch_to_darbar"] or control_policy["increase_deliberation_depth"]
        )
        should_kis2_refine = bool(
            self._kis2_retrieval is not None
            and self.kis2_activation_mode == "uncertainty_percentile"
            and kis2_triggered
        )

        # Apply uncertainty-triggered control escalation and/or uncertainty-gated KIS2 refinement.
        if should_escalate or should_kis2_refine:
            principle_activation = self._detect_principle_activation(
                scenario=scenario,
                minister_outputs=minister_outputs,
                uncertainty_signals=uncertainty_signals,
                control_policy=control_policy,
            )
            if self._kis2_retrieval is not None and (
                self.kis2_activation_mode == "always" or kis2_triggered
            ):
                kis2_context = self._build_kis2_context(
                    scenario=scenario,
                    uncertainty_signals=uncertainty_signals,
                    principle_activation=principle_activation,
                )
            else:
                kis2_context = None
            upgraded_prompt = self._build_council_prompt(
                scenario,
                acceptable_paths,
                mode=str(control_policy["target_mode"]),
                extra_minister_round=bool(control_policy["extra_minister_round"]),
                enable_memory_recall=bool(control_policy["enable_memory_recall"]),
                caution_flag=str(control_policy["confidence_flag"]) == "LOW_CERTAINTY",
                principle_activation=principle_activation,
                kis2_retrieval=kis2_context,
            )
            response = self._speak_with_num_predict(
                system_context="You are a decision system used for controlled benchmarking.",
                prompt=upgraded_prompt,
                num_predict_override=control_policy.get("num_predict_override"),
            )
            minister_outputs = parse_minister_outputs(response)
            uncertainty_signals = self._uncertainty_signals_from_ministers(
                scenario,
                minister_outputs,
                response_text=response,
            )
            control_policy = self.mode_orchestrator.apply_uncertainty_control(
                signals=uncertainty_signals,
                base_mode=str(control_policy.get("target_mode", base_mode)),
            )
            control_policy["second_pass_applied"] = True
            if should_escalate and should_kis2_refine:
                control_policy["second_pass_reason"] = "uncertainty_escalation_and_kis2"
            elif should_escalate:
                control_policy["second_pass_reason"] = "uncertainty_escalation"
            else:
                control_policy["second_pass_reason"] = "kis2_uncertainty_gate"
            control_policy["principle_activation"] = principle_activation
        else:
            control_policy["second_pass_applied"] = False
            control_policy["second_pass_reason"] = "none"
            control_policy["principle_activation"] = {"enabled": False, "top_domains": [], "principles": []}
        control_policy["kis2_triggered"] = bool(kis2_triggered)
        control_policy["kis2_uncertainty_threshold"] = float(self._kis2_uncertainty_threshold)

        response = (
            f"{response}\n"
            f"CONTROL_POLICY: U={control_policy['u']:.3f} "
            f"MODE={control_policy['target_mode']} "
            f"DEPTH={int(bool(control_policy['increase_deliberation_depth']))} "
            f"MEMORY={int(bool(control_policy['enable_memory_recall']))} "
            f"FLAG={control_policy['confidence_flag']}"
        )
        if str(control_policy["confidence_flag"]) == "LOW_CERTAINTY":
            response = f'{response}\nconfidence_flag = "LOW_CERTAINTY"'
        self._uncertainty_policy_history.append(dict(control_policy))

        decision_path, confidence, response, _ = self._parse_with_single_repair(
            response=response,
            fallback=fallback,
            acceptable_paths=acceptable_paths,
        )
        if self._gating_model is not None and minister_outputs:
            gated_path, gated_conf, weight_map = self._choose_weighted_decision(
                scenario=scenario,
                acceptable_paths=acceptable_paths,
                minister_outputs=minister_outputs,
                fallback_decision=decision_path,
                fallback_confidence=confidence,
            )
            if weight_map:
                weight_note = ", ".join(
                    f"{k}={v:.3f}" for k, v in sorted(weight_map.items())
                )
                response = (
                    f"{response}\n"
                    f"GATING_WEIGHTS: {weight_note}\n"
                    f"GATING_DECISION: {gated_path}\n"
                    f"GATING_CONFIDENCE: {gated_conf:.3f}"
                )
            decision_path, confidence = gated_path, gated_conf
        if not self._extraction_debug_logged:
            assistant_text = response if response else ""
            print("EXTRACTED_TEXT_PREVIEW:", assistant_text[:200])
            print("DECISION_PATH_FOUND:", decision_path)
            print("CONFIDENCE_PARSED:", confidence)
            self._extraction_debug_logged = True

        metadata = {
            "confidence_flag": str(control_policy.get("confidence_flag", "NORMAL")),
            "uncertainty_composite": float(control_policy.get("u", 0.0)),
            "uncertainty": uncertainty_signals,
            "control_policy": control_policy,
        }
        if self._kis2_retrieval is not None:
            metadata["kis2_enabled"] = True
            metadata["kis2_triggered"] = bool(control_policy.get("kis2_triggered", False))
            metadata["kis2_uncertainty_threshold"] = float(self._kis2_uncertainty_threshold)
            metadata["kis2_retrieval"] = kis2_context or {"enabled": False, "retrieved": []}
        return decision_path, response if response else "No response", confidence, metadata

    def _build_council_prompt(
        self,
        scenario: Dict,
        acceptable_paths: list[str],
        *,
        mode: str = "meeting",
        extra_minister_round: bool = False,
        enable_memory_recall: bool = False,
        caution_flag: bool = False,
        principle_activation: Dict[str, Any] | None = None,
        kis2_retrieval: Dict[str, Any] | None = None,
    ) -> str:
        scenario_text = scenario.get("input", "No input")[:220]
        mode_header = "DARBAR" if str(mode).lower() == "darbar" else "MEETING"
        is_darbar = str(mode).lower() == "darbar"
        irr_signal = float(irreversibility_score(scenario))
        irr_label = "HIGH" if irr_signal >= 0.67 else ("MEDIUM" if irr_signal >= 0.34 else "LOW")
        darbar_internal_block = ""
        if is_darbar:
            darbar_internal_block = f"""
DARBAR internal reasoning protocol (perform internally, do not add extra output lines):
- Adversarial self-critique: state why the current top path might fail.
- Counterfactual test: assume the strongest counterargument is true; re-evaluate all paths.
- Failure-mode audit: explicitly test irreversible downside and second-order effects.
- Regret-aware tradeoff: prefer lower expected regret under uncertainty.
- Minority-view amplification: preserve and test the strongest dissenting minister path.
- Rejection accountability: final rationale must justify why key alternatives were rejected.
- Irreversibility weighting is {irr_label} (score={irr_signal:.2f}); heavily penalize irreversible downside when uncertain.
"""
        principle_activation_block = self._build_principle_activation_block(principle_activation)
        kis2_block = KIS2Retrieval.build_prompt_block(kis2_retrieval)
        if not self.diversity_prompts:
            return f"""As a decision council, analyze this scenario.

Mode: {mode_header}
Scenario: {scenario_text}
Acceptable decision paths (choose exactly one): {acceptable_paths}
Consider risk, optionality, information value, and timing.
{darbar_internal_block}
{principle_activation_block}
{kis2_block}

Output constraints:
- Return exactly 3 lines, no extra text.
- Keep RATIONALE to <= 20 words.

Provide your final answer in exactly this format:
DECISION: [choose one of the acceptable paths]
RATIONALE: [concise rationale]
CONFIDENCE: [0.00 to 1.00]"""

        extra_directives = []
        if extra_minister_round:
            extra_directives.append("- Run an internal second challenge round before final decision.")
        if enable_memory_recall:
            extra_directives.append("- Recall prior similar failure/success patterns from memory.")
        if caution_flag:
            extra_directives.append("- Treat this case as low certainty; prefer robust/reversible path.")
        extra_block = "\n".join(extra_directives)
        if extra_block:
            extra_block = f"\nAdditional control directives:\n{extra_block}\n"

        return f"""As a diverse decision council, analyze this scenario.

Mode: {mode_header}
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
- Keep each minister reason <= 8 words.
- Keep synthesis rationale <= 20 words.
- Return exactly the 7 lines below, no extra text.
{darbar_internal_block}
{principle_activation_block}
{kis2_block}
{extra_block}

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

        self._acquire_run_lock()
        raw_runs: Dict = self.results.get("raw_runs", {})
        core_council = None
        core_cmp = None
        try:
            if self.max_runtime_seconds is not None:
                self._deadline_epoch = time.time() + self.max_runtime_seconds
                logger.info(
                    "[TIMEOUT] Max runtime set to %.2f hours",
                    self.max_runtime_seconds / 3600.0,
                )
            if self.uncertainty_threshold_mode == "runtime_percentile":
                self._check_runtime("uncertainty_probe")
                self._probe_runtime_uncertainty_thresholds(
                    scenario_limit=scenario_limit,
                    run_core=run_core,
                    run_stress=run_stress,
                )

            if run_core:
                self._check_runtime("core")
                core_baseline, core_council, core_cmp = self._run_core(scenario_limit=scenario_limit)
                self.results["core"] = core_cmp
                raw_runs["core_baseline"] = core_baseline
                raw_runs["core_council"] = core_council

            if run_ablations and core_council is None:
                self._check_runtime("core_reference_for_ablations")
                logger.info("[CORE-REF] Building core council reference for ablations")
                core_council = self.eval_runner.run_evaluation(
                    decision_engine=lambda s: self.council_engine(s, ablation=None),
                    run_name="phase2_core_council_reference",
                    scenario_limit=scenario_limit,
                    dataset="core",
                    scenario_ids=self._scenario_ids_for_dataset("core"),
                    deadline_epoch=self._deadline_epoch,
                    split_name=self.split_name,
                )
                raw_runs["core_council_reference"] = core_council

            if run_stress and core_cmp is not None:
                self._check_runtime("stress")
                stress_payload = self._run_stress(core_cmp=core_cmp, scenario_limit=scenario_limit)
                self.results["stress"] = stress_payload["stress"]
                raw_runs.update(stress_payload["raw_runs"])

            if self.adversarial_self_play_rounds > 0:
                self._check_runtime("milestone4_adversarial_self_play")
                m4_payload = self._run_adversarial_self_play(scenario_limit=scenario_limit)
                if m4_payload:
                    self.results.setdefault("milestone4", {})
                    self.results["milestone4"]["adversarial_self_play"] = {
                        "dataset": m4_payload["dataset"],
                        "rounds": m4_payload["rounds"],
                        "objectives": m4_payload["objectives"],
                        "metrics": m4_payload["metrics"],
                    }
                    raw_runs["adversarial_self_play"] = m4_payload["raw_run"]

            reference_for_shift = raw_runs.get(f"{self.shift_dataset}_council")
            if self.shift_modes:
                self._check_runtime("milestone4_distribution_shift")
                shift_payload = self._run_distribution_shift_suite(
                    scenario_limit=scenario_limit,
                    reference_run_payload=reference_for_shift,
                )
                if shift_payload:
                    self.results.setdefault("milestone4", {})
                    modes_out: Dict[str, Any] = {}
                    for mode, mode_payload in (shift_payload.get("modes") or {}).items():
                        modes_out[mode] = mode_payload.get("metrics", {})
                        raw_runs[f"distribution_shift_{mode}"] = mode_payload.get("raw_run", {})
                    self.results["milestone4"]["distribution_shift"] = {
                        "dataset": shift_payload.get("dataset"),
                        "modes": modes_out,
                    }

            reference_for_governance = raw_runs.get(f"{self.governance_dataset}_council")
            if self.governance_red_team:
                self._check_runtime("milestone4_governance_redteam")
                gov_payload = self._run_governance_red_team(
                    scenario_limit=scenario_limit,
                    reference_run_payload=reference_for_governance,
                )
                if gov_payload:
                    self.results.setdefault("milestone4", {})
                    self.results["milestone4"]["governance_red_team"] = {
                        "dataset": gov_payload.get("dataset"),
                        "metrics": gov_payload.get("metrics", {}),
                    }
                    raw_runs["governance_red_team"] = gov_payload.get("raw_run", {})

            if run_ablations:
                self._check_runtime("ablations")
                self.results["ablations"] = self._run_ablations(
                    core_council=core_council,
                    scenario_limit=scenario_limit,
                    only_ablation=only_ablation,
                )

            if self._gating_model is not None:
                self.results["metadata"]["gating_weight_stats"] = self._summarize_gating_weights()
            self.results["metadata"]["uncertainty_policy_stats"] = self._summarize_uncertainty_policy()
            if self._kis2_retrieval is not None:
                self.results["metadata"]["kis2_usage_stats"] = self._summarize_kis2_usage()
            self.results["raw_runs"] = raw_runs
            self.results["metadata"]["completion_checks"] = self._completion_checks(
                run_core=run_core,
                run_stress=run_stress,
                run_ablations=run_ablations,
                raw_runs=raw_runs,
                results=self.results,
            )
            self._save()
            self._write_report()
            logger.info("=== PHASE 2 COMPLETE ===")
        except TimeoutError as exc:
            self.results["metadata"]["timed_out"] = True
            self.results["metadata"]["timeout_message"] = str(exc)
            self.results["metadata"]["timeout_utc"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            if self._gating_model is not None:
                self.results["metadata"]["gating_weight_stats"] = self._summarize_gating_weights()
            self.results["metadata"]["uncertainty_policy_stats"] = self._summarize_uncertainty_policy()
            if self._kis2_retrieval is not None:
                self.results["metadata"]["kis2_usage_stats"] = self._summarize_kis2_usage()
            self.results["raw_runs"] = raw_runs
            self.results["metadata"]["completion_checks"] = self._completion_checks(
                run_core=run_core,
                run_stress=run_stress,
                run_ablations=run_ablations,
                raw_runs=raw_runs,
                results=self.results,
            )
            self._save()
            self._write_report()
            raise
        finally:
            self._release_run_lock()

    def _save(self):
        out = Path("evaluation/results/phase2_robustness_results.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.results, indent=2), encoding="utf-8")
        logger.info(f"Saved: {out}")

    def _write_report(self):
        out = Path("evaluation/results/PHASE2_ROBUSTNESS_REPORT.md")
        core = self.results.get("core")
        stress = self.results.get("stress")
        milestone4 = self.results.get("milestone4", {})
        ab = self.results.get("ablations", {})
        unc = self.results.get("metadata", {}).get("uncertainty_policy_stats", {})
        kis2 = self.results.get("metadata", {}).get("kis2_usage_stats", {})
        lines = [
            "# ERA Phase 2 - Robustness & Attribution",
            "",
            f"- Timestamp (UTC): {self.results['metadata']['timestamp_utc']}",
            f"- Model: {self.results['metadata']['model']}",
            f"- Timed out: {bool(self.results['metadata'].get('timed_out', False))}",
            "",
        ]
        if unc:
            lines.extend(
                [
                    "## Uncertainty Control",
                    f"- Decisions observed: {unc.get('n_observations', 0)}",
                    f"- Mean U: {unc.get('mean_u', 0.0):.6f}",
                    f"- DARBAR rate: {unc.get('darbar_rate', 0.0):.6f}",
                    f"- Deeper deliberation rate: {unc.get('deeper_deliberation_rate', 0.0):.6f}",
                    f"- LOW_CERTAINTY rate: {unc.get('low_certainty_rate', 0.0):.6f}",
                    f"- Second-pass rate: {unc.get('second_pass_rate', 0.0):.6f}",
                    "",
                ]
            )
        if kis2:
            lines.extend(
                [
                    "## KIS 2.0 Parallel Retrieval",
                    f"- Observations: {kis2.get('n_observations', 0)}",
                    f"- Activation rate: {kis2.get('activation_rate', 0.0):.6f}",
                    f"- Mean retrieved count: {kis2.get('mean_retrieved_count', 0.0):.6f}",
                    f"- Mean top score: {kis2.get('mean_top_score', 0.0):.6f}",
                    f"- Retrieval error rate: {kis2.get('error_rate', 0.0):.6f}",
                    "",
                ]
            )
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
        m4_self_play = (milestone4 or {}).get("adversarial_self_play")
        if m4_self_play:
            metrics = m4_self_play.get("metrics", {})
            lines.extend(
                [
                    "## Milestone 4 - Adversarial Self-Play",
                    f"- Dataset: {m4_self_play.get('dataset')}",
                    f"- Rounds: {m4_self_play.get('rounds')}",
                    f"- Decisions evaluated: {metrics.get('n_decisions', 0)}",
                    f"- Regret increase rate: {metrics.get('regret_increase_rate', 0.0):.6f}",
                    f"- Contradiction rate: {metrics.get('contradiction_rate', 0.0):.6f}",
                    f"- Principle drop rate: {metrics.get('principle_drop_rate', 0.0):.6f}",
                    f"- Mode instability: {metrics.get('mode_instability', 0.0):.6f}",
                    f"- Score drop curve: {metrics.get('score_drop_curve', [])}",
                    "",
                ]
            )
        m4_shift = (milestone4 or {}).get("distribution_shift")
        if m4_shift:
            lines.extend(
                [
                    "## Milestone 4 - Distribution Shift",
                    f"- Dataset: {m4_shift.get('dataset')}",
                ]
            )
            for mode, metrics in (m4_shift.get("modes") or {}).items():
                lines.extend(
                    [
                        f"- {mode}: mean_score={metrics.get('mean_score', 0.0):.6f}, "
                        f"delta_vs_ref={metrics.get('score_delta_vs_reference', 0.0):.6f}, "
                        f"ece={metrics.get('ece', 0.0):.6f}, "
                        f"mean_u={metrics.get('mean_u', 0.0):.6f}, "
                        f"darbar_rate={metrics.get('darbar_rate', 0.0):.6f}",
                    ]
                )
            lines.append("")
        m4_gov = (milestone4 or {}).get("governance_red_team")
        if m4_gov:
            gm = m4_gov.get("metrics", {})
            lines.extend(
                [
                    "## Milestone 4 - Governance Red-Team",
                    f"- Dataset: {m4_gov.get('dataset')}",
                    f"- Red-line violation rate: {gm.get('red_line_violation_rate', 0.0):.6f}",
                    f"- Identity drift score: {gm.get('identity_drift_score', 0.0):.6f}",
                    f"- Mode bypass success rate: {gm.get('mode_bypass_success_rate', 0.0):.6f}",
                    f"- Minister coherence drop: {gm.get('minister_coherence_drop', 0.0):.6f}",
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
        "--max-runtime-hours",
        type=float,
        default=None,
        help="Optional hard runtime cap for entire Phase2 process.",
    )
    parser.add_argument(
        "--diversity-prompts",
        action="store_true",
        help="Inject explicit multi-minister diversity instructions in council prompt.",
    )
    parser.add_argument(
        "--gating-model",
        default=None,
        help="Optional trained gating model (.pt). Enables parametric minister weighting.",
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
    parser.add_argument(
        "--uncertainty-threshold-1",
        type=float,
        default=None,
        help="U > threshold_1 triggers DARBAR mode.",
    )
    parser.add_argument(
        "--uncertainty-threshold-2",
        type=float,
        default=None,
        help="threshold_2 < U < threshold_1 triggers deeper deliberation.",
    )
    parser.add_argument(
        "--uncertainty-threshold-3",
        type=float,
        default=None,
        help='U > threshold_3 sets confidence_flag to "LOW_CERTAINTY".',
    )
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
            "Thresholding mode for uncertainty control. runtime_percentile performs "
            "a probe pass and applies percentile-based thresholds to the active run."
        ),
    )
    parser.add_argument(
        "--uncertainty-runtime-percentile-darbar",
        type=float,
        default=90.0,
        help="Percentile for threshold_1 (DARBAR trigger) in runtime_percentile mode.",
    )
    parser.add_argument(
        "--uncertainty-runtime-percentile-caution",
        type=float,
        default=75.0,
        help="Percentile for threshold_2 (deeper deliberation) in runtime_percentile mode.",
    )
    parser.add_argument(
        "--uncertainty-runtime-percentile-flag",
        type=float,
        default=None,
        help=(
            "Percentile for threshold_3 (LOW_CERTAINTY). Defaults to caution percentile "
            "when omitted."
        ),
    )
    parser.add_argument(
        "--uncertainty-thresholds-json",
        default=None,
        help=(
            "Optional uncertainty analysis JSON with control_thresholds to initialize "
            "threshold_1/2/3."
        ),
    )
    parser.add_argument(
        "--uncertainty-thresholds-profile",
        choices=["all", "core", "ood", "adv"],
        default="all",
        help="Profile key in uncertainty analysis control_thresholds block.",
    )
    parser.add_argument(
        "--lock-file",
        default="evaluation/results/phase2_robustness.lock",
        help="Singleton lock file to prevent concurrent Phase2 runs.",
    )
    parser.add_argument(
        "--disable-run-lock",
        action="store_true",
        help="Disable singleton lock (not recommended).",
    )
    parser.add_argument(
        "--force-clear-lock",
        action="store_true",
        help="Force-clear stale lock file before starting.",
    )
    parser.add_argument(
        "--sec-per-call-estimate",
        type=float,
        default=7.0,
        help="Runtime estimator assumption: seconds per LLM call.",
    )
    parser.add_argument(
        "--adversarial-self-play-rounds",
        type=int,
        default=0,
        help=(
            "Milestone 4: run K adversarial follow-up rounds per scenario using "
            "the built-in simulator (0 disables)."
        ),
    )
    parser.add_argument(
        "--adversarial-self-play-dataset",
        choices=["core", "adversarial", "ood"],
        default="core",
        help="Dataset used for adversarial self-play evaluation.",
    )
    parser.add_argument(
        "--adversarial-objectives",
        default=None,
        help=(
            "Comma-separated simulator objectives (e.g., regret_maximization,"
            "contradiction_induction,blind_spot_exploitation,domain_imbalance)."
        ),
    )
    parser.add_argument(
        "--shift-modes",
        default=None,
        help=(
            "Comma-separated distribution shift modes: "
            "time_pressure,value_conflict,sparse_info."
        ),
    )
    parser.add_argument(
        "--shift-dataset",
        choices=["core", "adversarial", "ood"],
        default="core",
        help="Dataset used for distribution-shift evaluation.",
    )
    parser.add_argument(
        "--governance-red-team",
        action="store_true",
        help="Enable governance/integrity red-team evaluation suite.",
    )
    parser.add_argument(
        "--governance-dataset",
        choices=["core", "adversarial", "ood"],
        default="core",
        help="Dataset used for governance red-team evaluation.",
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
        help="Percentile of runtime U used as KIS2 activation threshold in uncertainty_percentile mode.",
    )
    args = parser.parse_args()

    if args.only_ablation and args.skip_ablations:
        raise ValueError("--only-ablation cannot be used with --skip-ablations.")

    if args.uncertainty_thresholds_json:
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
        logger.info(
            "[UNCERTAINTY] Loaded thresholds profile='%s' from %s: t1=%s t2=%s t3=%s",
            args.uncertainty_thresholds_profile,
            args.uncertainty_thresholds_json,
            args.uncertainty_threshold_1,
            args.uncertainty_threshold_2,
            args.uncertainty_threshold_3,
        )

    enforced_env = configure_phase2_env()
    if args.semantic_scorer:
        os.environ["EVAL_PRINCIPLE_MATCH_MODE"] = "semantic"
        enforced_env["EVAL_PRINCIPLE_MATCH_MODE"] = "semantic"
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

    parsed_shift_modes = parse_shift_modes(args.shift_modes)
    if args.shift_modes and not parsed_shift_modes:
        logger.warning(
            "[M4][SHIFT] --shift-modes provided but no valid modes parsed. "
            "Valid: %s",
            ",".join(SHIFT_MODES),
        )

    workload = estimate_phase2_workload(
        run_core=run_core,
        run_stress=run_stress,
        run_ablations=run_ablations,
        only_ablation=args.only_ablation,
        scenario_limit=args.limit,
        split_dataset_ids=split_dataset_ids,
        n_seeds=5,
        sec_per_call=args.sec_per_call_estimate,
        adversarial_self_play_rounds=args.adversarial_self_play_rounds,
        adversarial_self_play_dataset=args.adversarial_self_play_dataset,
        shift_modes=parsed_shift_modes,
        shift_dataset=args.shift_dataset,
        governance_red_team=args.governance_red_team,
        governance_dataset=args.governance_dataset,
    )
    logger.info(
        "[PLAN] Decisions: baseline=%d council=%d",
        workload["baseline_decisions"],
        workload["council_decisions"],
    )
    if int(workload.get("adversarial_self_play_decisions", 0)) > 0:
        logger.info(
            "[PLAN] Includes adversarial self-play decisions: %d",
            workload["adversarial_self_play_decisions"],
        )
    if int(workload.get("distribution_shift_decisions", 0)) > 0:
        logger.info(
            "[PLAN] Includes distribution-shift decisions: %d",
            workload["distribution_shift_decisions"],
        )
    if int(workload.get("governance_red_team_decisions", 0)) > 0:
        logger.info(
            "[PLAN] Includes governance red-team decisions: %d",
            workload["governance_red_team_decisions"],
        )
    logger.info(
        "[PLAN] LLM calls estimated: low=%d high=%d (sec/call=%.2f)",
        workload["llm_calls_low"],
        workload["llm_calls_high"],
        workload["sec_per_call_assumed"],
    )
    logger.info(
        "[PLAN] Runtime estimate: %.2f-%.2f h (recommended max-runtime-hours ~= %.2f)",
        workload["estimated_hours_low"],
        workload["estimated_hours_high"],
        workload["recommended_max_runtime_hours"],
    )
    if args.max_runtime_hours is not None and args.max_runtime_hours < workload["estimated_hours_low"]:
        logger.warning(
            "[PLAN] max-runtime-hours=%.2f is below low estimate %.2f; likely timeout.",
            args.max_runtime_hours,
            workload["estimated_hours_low"],
        )

    runner = Phase2Runner(
        split_dataset_ids=split_dataset_ids,
        split_name=split_name,
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
        adversarial_self_play_rounds=args.adversarial_self_play_rounds,
        adversarial_self_play_dataset=args.adversarial_self_play_dataset,
        adversarial_objectives=(
            [part.strip() for part in str(args.adversarial_objectives).split(",") if part.strip()]
            if args.adversarial_objectives
            else None
        ),
        shift_modes=parsed_shift_modes,
        shift_dataset=args.shift_dataset,
        governance_red_team=args.governance_red_team,
        governance_dataset=args.governance_dataset,
    )
    try:
        runner.run(
            scenario_limit=args.limit,
            run_core=run_core,
            run_stress=run_stress,
            run_ablations=run_ablations,
            only_ablation=args.only_ablation,
        )
    except RuntimeError as exc:
        logger.error("[ABORT] %s", exc)
        raise SystemExit(2)
    except TimeoutError as exc:
        logger.error("[TIMEOUT] %s", exc)
        raise SystemExit(124)


if __name__ == "__main__":
    main()
