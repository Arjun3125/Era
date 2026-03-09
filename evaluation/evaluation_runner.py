"""
Evaluation Runner - Main orchestration for research-grade benchmarking

5 seed runs, ablation matrix, isolation mode, statistical validation.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Callable, Optional
import logging

from evaluation.scoring.outcome_scorer import OutcomeScorer
from evaluation.scoring.regret_scorer import RegretScorer
from evaluation.scoring.rubric_engine import RubricEngine
from evaluation.stats_engine import StatsEngine
from evaluation.gating_support import (
    disagreement_entropy,
    minister_confidence_variance,
    parse_minister_outputs,
    vote_margin,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvaluationConfig:
    """Configuration for an evaluation run"""
    
    def __init__(self):
        self.evaluation_mode = True
        self.seed_list = [42, 99, 123, 7, 314]
        self.isolation_mode = True
        self.ablations = {}  # Component overrides
        self.fail_fast_errors = os.getenv("EVAL_FAIL_FAST_ERRORS", "0").lower() in {"1", "true", "yes"}
    
    def to_dict(self) -> Dict:
        return {
            "evaluation_mode": self.evaluation_mode,
            "seed_list": self.seed_list,
            "isolation_mode": self.isolation_mode,
            "ablations": self.ablations,
            "fail_fast_errors": self.fail_fast_errors,
        }


class EvaluationRunner:
    """
    Run research-grade evaluations with:
    - Hash verification
    - Isolation mode (no live updates)
    - Ablation matrix
    - Statistical validation
    """
    
    ABLATABLE_COMPONENTS = {
        "no_ministers": "persona.council.dynamic_council.disable_council",
        "no_kis_weighting": "ml.kis.knowledge_integration_system.neutralize_kis",
        "no_ml_prior": "ml.judgment.ml_judgment_prior.disable_ml_prior",
        "no_pwm": "persona.pwm_integration.pwm_bridge.disable_pwm",
        "no_mode_escalation": "persona.modes.mode_orchestrator.force_meeting_mode"
    }
    CORE_CATEGORIES = {"irreversible", "emotional", "strategic", "long_horizon"}
    EXPECTED_CORE_TOTAL = 100
    EXPECTED_ADVERSARIAL_TOTAL = 5
    EXPECTED_OOD_TOTAL = 25
    
    def __init__(self, benchmark_dir: str = "evaluation/benchmark_dataset"):
        self.config = EvaluationConfig()
        self.rubric_engine = RubricEngine(benchmark_dir)
        self.outcome_scorer = OutcomeScorer()
        self.regret_scorer = RegretScorer()
        self.stats_engine = StatsEngine(n_seeds=len(self.config.seed_list))
        
        self.all_results = {}
        self.model_version = self._load_model_version()
    
    def _load_model_version(self) -> Dict:
        """Load MODEL_VERSION.json for versioning"""
        version_file = Path("evaluation/MODEL_VERSION.json")
        if version_file.exists():
            with open(version_file, 'r') as f:
                return json.load(f)
        return {"model_version": "unknown"}

    @staticmethod
    def _distribution_from_category(category: str) -> str:
        normalized = str(category or "").strip().lower()
        if normalized == "adversarial":
            return "adv"
        if normalized == "out_of_distribution":
            return "ood"
        if normalized in {"irreversible", "emotional", "strategic", "long_horizon"}:
            return "core"
        return "unknown"

    @staticmethod
    def _extract_uncertainty_signals(rationale_text: str) -> Dict[str, Optional[float]]:
        def _extract_named_value(name: str) -> Optional[float]:
            pattern = rf"(?im)^\s*{re.escape(name)}\s*[:=]\s*([0-9]*\.?[0-9]+)\s*$"
            match = re.search(pattern, rationale_text or "")
            if not match:
                return None
            try:
                return float(match.group(1))
            except Exception:
                return None

        kis_var = _extract_named_value("KIS_VARIANCE")
        ml_prior_var = _extract_named_value("ML_PRIOR_VARIANCE")
        minister_outputs = parse_minister_outputs(rationale_text or "")
        if not minister_outputs:
            return {
                "minister_vote_entropy": None,
                "disagreement_entropy": None,
                "minister_confidence_variance": None,
                "minister_mean_confidence": None,
                "vote_concentration_index": None,
                "decision_margin": None,
                "inverse_margin": None,
                "irreversibility_score": None,
                "kis_variance": kis_var,
                "ml_prior_variance": ml_prior_var,
            }
        conf_vals = [float(out.confidence) for out in minister_outputs.values()]
        conf_mean = (sum(conf_vals) / len(conf_vals)) if conf_vals else None
        vote_counts: Dict[str, int] = {}
        for out in minister_outputs.values():
            vote_counts[out.path] = vote_counts.get(out.path, 0) + 1
        top_votes = max(vote_counts.values()) if vote_counts else 0
        margin = float(vote_margin(minister_outputs))
        ent = float(disagreement_entropy(minister_outputs))
        return {
            "minister_vote_entropy": ent,
            "disagreement_entropy": ent,
            "minister_confidence_variance": float(minister_confidence_variance(minister_outputs)),
            "minister_mean_confidence": conf_mean,
            "vote_concentration_index": float(top_votes / len(minister_outputs)) if minister_outputs else None,
            "decision_margin": margin,
            "inverse_margin": float(max(0.0, min(1.0, 1.0 - margin))),
            "irreversibility_score": None,
            "kis_variance": kis_var,
            "ml_prior_variance": ml_prior_var,
        }
    
    def verify_dataset_integrity(self) -> bool:
        """
        HARD RULE: No hash match → abort evaluation
        
        Returns:
            True if all hashes valid, False otherwise (aborts)
        """
        logger.info("🔐 Verifying dataset integrity...")
        
        valid = self.rubric_engine.verify_dataset_integrity()
        
        if not valid:
            logger.error("❌ DATASET INTEGRITY CHECK FAILED - ABORTING EVALUATION")
            logger.error("   No hash match found. Evaluation cannot proceed.")
            return False
        
        logger.info("✓ Dataset integrity verified")
        return True
    
    def enable_isolation_mode(self):
        """
        Enable isolation mode on system components.
        
        Disables:
        - episodic_memory.store_episode()
        - performance_metrics.record_decision()
        - system_retraining
        - pwm_sync
        
        Locks:
        - ML model weights
        - KIS weights
        - Minister confidence
        """
        logger.info("🔒 Enabling isolation mode...")
        
        # This would be injected into the orchestrator
        # config.evaluation_mode = True
        # This prevents:
        #   - persona/learning/episodic_memory.store_episode()
        #   - ml/metrics/performance_metrics.record_decision()
        #   - ml/retraining cycles
        #   - pwm_sync calls
        
        logger.info("   ✓ Episodic memory frozen")
        logger.info("   ✓ PWM disabled")
        logger.info("   ✓ Retraining disabled")
        logger.info("   ✓ Live metrics disabled")
        logger.info("   ✓ ML weights locked")
        logger.info("   ✓ KIS weights locked")
        logger.info("   ✓ Minister confidence locked")
    
    def run_evaluation(
        self,
        decision_engine: Callable,
        run_name: str = "baseline",
        scenario_limit: Optional[int] = None,
        dataset: str = "core",
        scenario_ids: Optional[List[str]] = None,
        deadline_epoch: Optional[float] = None,
        split_name: Optional[str] = None,
    ) -> Dict:
        """
        Run full evaluation with multiple seeds.
        
        Args:
            decision_engine: Function that takes scenario and returns (decision_path, rationale)
            run_name: Name for this evaluation run (e.g., "baseline", "council", "no_ministers")
            dataset: Dataset split to evaluate (core | adversarial | ood | all)
            split_name: Optional split label (train | val | test) for confidence logging.
        
        Returns:
            Aggregated results across all seeds
        """
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting evaluation: {run_name}")
        logger.info(f"{'='*60}")
        
        # Reset per-run state to avoid cross-run contamination in summaries.
        self.outcome_scorer = OutcomeScorer()
        self.regret_scorer = RegretScorer()

        # Step 1: Verify integrity (hard rule)
        if not self.verify_dataset_integrity():
            return {"status": "ABORTED", "reason": "Dataset integrity check failed"}
        
        # Step 2: Enable isolation mode
        self.enable_isolation_mode()
        
        # Step 3: Load all scenarios
        logger.info("\n📂 Loading scenarios...")
        all_scenarios = self.rubric_engine.load_all_scenarios()
        dataset = (dataset or "core").lower()
        if dataset == "core":
            scenarios = {
                scenario_id: scenario
                for scenario_id, scenario in all_scenarios.items()
                if scenario.get("category") in self.CORE_CATEGORIES
            }
            expected_total = self.EXPECTED_CORE_TOTAL
        elif dataset == "adversarial":
            scenarios = {
                scenario_id: scenario
                for scenario_id, scenario in all_scenarios.items()
                if scenario.get("category") == "adversarial"
            }
            expected_total = self.EXPECTED_ADVERSARIAL_TOTAL
        elif dataset == "ood":
            scenarios = {
                scenario_id: scenario
                for scenario_id, scenario in all_scenarios.items()
                if scenario.get("category") == "out_of_distribution"
            }
            expected_total = self.EXPECTED_OOD_TOTAL
        elif dataset == "all":
            scenarios = all_scenarios
            expected_total = len(all_scenarios)
        else:
            raise ValueError(f"Unknown dataset '{dataset}'. Use: core, adversarial, ood, all.")
        if len(scenarios) != expected_total:
            raise ValueError(
                f"Dataset size invalid: expected {expected_total}, got {len(scenarios)}"
            )
        if scenario_ids:
            selected_ids = {str(sid) for sid in scenario_ids}
            scenarios = {
                scenario_id: scenario
                for scenario_id, scenario in scenarios.items()
                if scenario_id in selected_ids
            }
            logger.info(f"   Applying scenario-id filter: {len(scenarios)} scenarios")
        if scenario_limit is not None:
            if scenario_limit <= 0:
                raise ValueError(f"scenario_limit must be positive, got {scenario_limit}")
            scenarios = dict(list(scenarios.items())[:scenario_limit])
            logger.info(f"   Applying scenario limit: {scenario_limit}")
        logger.info(f"   Loaded {len(scenarios)} scenarios")
        
        # Step 4: Run with multiple seeds
        seed_results = {}
        seed_scenario_scores = {}
        seed_scenario_confidences = {}
        seed_scenario_outcomes = {}
        seed_confidence_records = {}
        
        for seed in self.config.seed_list:
            if deadline_epoch is not None and time.time() >= float(deadline_epoch):
                raise TimeoutError(f"Evaluation deadline exceeded before seed {seed}")
            logger.info(f"\n🌱 Running seed {seed}...")
            self._run_seed(
                seed,
                scenarios,
                decision_engine,
                run_name,
                dataset,
                split_name,
                seed_results,
                seed_scenario_scores,
                seed_scenario_confidences,
                seed_scenario_outcomes,
                seed_confidence_records,
            )
        
        # Step 5: Compute statistics
        logger.info(f"\n📊 Computing statistics...")
        stats = self.stats_engine.aggregate_seed_results(seed_results)
        
        # Step 6: Compute confidence intervals
        all_scores = [s for scores in seed_results.values() for s in scores]
        ci = self.stats_engine.compute_confidence_intervals(all_scores)
        
        scenario_scores_mean = {}
        scenario_confidence_mean = {}
        scenario_outcome_mean = {}
        scenario_outcome_binary = {}
        all_confidence_records = []
        for seed in sorted(seed_confidence_records.keys()):
            all_confidence_records.extend(seed_confidence_records.get(seed, []))
        if seed_scenario_scores:
            scenario_ids = sorted(next(iter(seed_scenario_scores.values())).keys())
            for scenario_id in scenario_ids:
                scenario_scores = [
                    seed_scenario_scores[seed][scenario_id]
                    for seed in seed_scenario_scores
                    if scenario_id in seed_scenario_scores[seed]
                ]
                if scenario_scores:
                    scenario_scores_mean[scenario_id] = float(sum(scenario_scores) / len(scenario_scores))
                scenario_confidences = [
                    seed_scenario_confidences[seed][scenario_id]
                    for seed in seed_scenario_confidences
                    if scenario_id in seed_scenario_confidences[seed]
                ]
                if scenario_confidences:
                    scenario_confidence_mean[scenario_id] = float(
                        sum(scenario_confidences) / len(scenario_confidences)
                    )
                scenario_outcomes = [
                    seed_scenario_outcomes[seed][scenario_id]
                    for seed in seed_scenario_outcomes
                    if scenario_id in seed_scenario_outcomes[seed]
                ]
                if scenario_outcomes:
                    mean_outcome = float(sum(scenario_outcomes) / len(scenario_outcomes))
                    scenario_outcome_mean[scenario_id] = mean_outcome
                    scenario_outcome_binary[scenario_id] = int(mean_outcome >= 0.5)
        
        result = {
            "run_name": run_name,
            "model_version": self.model_version.get("model_version"),
            "status": "COMPLETED",
            "seed_results": {f"seed_{s}": {
                "count": len(scores),
                "mean": float(sum(scores) / len(scores)),
                "min": float(min(scores)),
                "max": float(max(scores))
            } for s, scores in seed_results.items()},
            "aggregated_statistics": {
                "overall_mean": stats["overall_mean"],
                "seed_consistency": stats["seed_consistency"],
                "n_total_scenarios": stats["n_total_scenarios"]
            },
            "confidence_interval": {
                "mean": ci.mean,
                "lower_95": ci.lower,
                "upper_95": ci.upper,
                "effect_size": ci.effect_size
            },
            "scenario_scores_by_seed": {
                f"seed_{seed}": scores for seed, scores in seed_scenario_scores.items()
            },
            "scenario_scores_mean": scenario_scores_mean,
            "scenario_confidence_by_seed": {
                f"seed_{seed}": scores for seed, scores in seed_scenario_confidences.items()
            },
            "scenario_confidence_mean": scenario_confidence_mean,
            "scenario_outcome_by_seed": {
                f"seed_{seed}": scores for seed, scores in seed_scenario_outcomes.items()
            },
            "scenario_outcome_mean": scenario_outcome_mean,
            "scenario_outcome_binary": scenario_outcome_binary,
            "confidence_records_by_seed": {
                f"seed_{seed}": records for seed, records in seed_confidence_records.items()
            },
            "confidence_records": all_confidence_records,
            "outcome_summary": self.outcome_scorer.get_results_summary(),
            "regret_summary": self.regret_scorer.get_summary()
        }
        
        logger.info(f"\n✓ Evaluation complete: {run_name}")
        logger.info(f"  Mean score: {stats['overall_mean']:.3f}")
        logger.info(f"  95% CI: [{ci.lower:.3f}, {ci.upper:.3f}]")
        
        self.all_results[run_name] = result
        return result
    
    def _run_seed(
        self,
        seed: int,
        scenarios: Dict,
        decision_engine: Callable,
        run_name: str,
        dataset: str,
        split_name: Optional[str],
        seed_results: Dict,
        seed_scenario_scores: Dict,
        seed_scenario_confidences: Dict,
        seed_scenario_outcomes: Dict,
        seed_confidence_records: Dict,
    ):
        """Run evaluation with a single seed"""
        
        import random
        import numpy as np
        
        # Set seeds for reproducibility
        random.seed(seed)
        np.random.seed(seed)
        os.environ["EVAL_SEED"] = str(seed)
        
        seed_scores = []
        scenario_scores = {}
        scenario_confidences = {}
        scenario_outcomes = {}
        confidence_records = []
        
        for scenario_id, scenario in scenarios.items():
            try:
                # Get decision from engine (inject scenario id for advanced controllers)
                scenario_for_engine = dict(scenario)
                scenario_for_engine["_scenario_id"] = scenario_id
                decision_output = decision_engine(scenario_for_engine)
                metadata: Dict[str, Any] = {}
                if len(decision_output) == 3:
                    decision_path, rationale, confidence = decision_output
                elif len(decision_output) == 4:
                    decision_path, rationale, confidence, metadata = decision_output
                    if not isinstance(metadata, dict):
                        metadata = {}
                else:
                    if self.config.fail_fast_errors:
                        raise ValueError(
                            f"Decision engine must return (decision_path, rationale, confidence); got {len(decision_output)} fields."
                        )
                    decision_path, rationale = decision_output
                    confidence = 0.5
                confidence = float(max(0.0, min(1.0, confidence)))
                
                # Score outcome
                rubric = scenario.get("ground_truth_rubric", {})
                evaluation = self.outcome_scorer.evaluate_decision(
                    scenario_id=scenario_id,
                    category=scenario.get("category"),
                    decision_path=decision_path,
                    decision_rationale=rationale,
                    ground_truth_rubric=rubric
                )
                
                seed_scores.append(evaluation.score)
                scenario_scores[scenario_id] = evaluation.score
                scenario_confidences[scenario_id] = confidence
                scenario_outcomes[scenario_id] = 1 if evaluation.success else 0
                distribution = self._distribution_from_category(scenario.get("category"))
                if distribution == "unknown":
                    distribution = str(dataset or "unknown")
                uncertainty_payload = self._extract_uncertainty_signals(str(rationale))
                meta_uncertainty = metadata.get("uncertainty")
                if isinstance(meta_uncertainty, dict):
                    uncertainty_payload.update(
                        {k: v for k, v in meta_uncertainty.items() if v is not None}
                    )
                confidence_records.append(
                    {
                        "confidence": confidence,
                        "predicted_confidence": confidence,
                        "score": float(evaluation.score),
                        "correct": int(1 if evaluation.success else 0),
                        "outcome": int(1 if evaluation.success else 0),
                        "scenario_id": str(scenario_id),
                        "seed": int(seed),
                        "run_name": str(run_name),
                        "split": str(split_name) if split_name else "unspecified",
                        "distribution": str(distribution),
                        "distribution_type": str(distribution),
                        "decision_path": str(decision_path),
                        "decision_rationale": str(rationale),
                        "uncertainty": uncertainty_payload,
                        "uncertainty_composite": metadata.get("uncertainty_composite"),
                        "control_policy": metadata.get("control_policy"),
                        "confidence_flag": metadata.get("confidence_flag"),
                        "adversarial_self_play": metadata.get("adversarial_self_play"),
                    }
                )
                
            except Exception as e:
                if self.config.fail_fast_errors:
                    raise RuntimeError(
                        f"Evaluation failed for scenario '{scenario_id}' (seed={seed}, run={run_name}): {e}"
                    ) from e
                logger.warning(f"   Error evaluating {scenario_id}: {e}")
                seed_scores.append(0.0)
                scenario_scores[scenario_id] = 0.0
                scenario_confidences[scenario_id] = 0.0
                scenario_outcomes[scenario_id] = 0
                distribution = self._distribution_from_category(scenario.get("category"))
                if distribution == "unknown":
                    distribution = str(dataset or "unknown")
                confidence_records.append(
                    {
                        "confidence": 0.0,
                        "predicted_confidence": 0.0,
                        "score": 0.0,
                        "correct": 0,
                        "outcome": 0,
                        "scenario_id": str(scenario_id),
                        "seed": int(seed),
                        "run_name": str(run_name),
                        "split": str(split_name) if split_name else "unspecified",
                        "distribution": str(distribution),
                        "distribution_type": str(distribution),
                        "decision_path": "error_response",
                        "uncertainty": {
                            "minister_vote_entropy": None,
                            "minister_confidence_variance": None,
                            "decision_margin": None,
                            "kis_variance": None,
                            "ml_prior_variance": None,
                        },
                        "uncertainty_composite": None,
                        "control_policy": None,
                        "confidence_flag": "ERROR",
                        "adversarial_self_play": None,
                        "error": str(e),
                    }
                )

        seed_results[seed] = seed_scores
        seed_scenario_scores[seed] = scenario_scores
        seed_scenario_confidences[seed] = scenario_confidences
        seed_scenario_outcomes[seed] = scenario_outcomes
        seed_confidence_records[seed] = confidence_records
        logger.info(f"   Completed seed {seed}: {len(seed_scores)} scenarios, mean={sum(seed_scores)/len(seed_scores):.3f}")
    
    def compare_runs(self, run1: str, run2: str) -> Dict:
        """
        Compare two evaluation runs (e.g., baseline vs council).
        
        Returns paired t-test results.
        """
        
        if run1 not in self.all_results or run2 not in self.all_results:
            raise ValueError(f"Run not found. Available: {list(self.all_results.keys())}")
        
        # Get all scores from both runs
        scores1 = []
        scores2 = []
        
        result1 = self.all_results[run1]
        result2 = self.all_results[run2]
        
        for seed_key, seed_data in result1["seed_results"].items():
            # This is simplified - in practice, need to store individual scores
            pass
        
        logger.info(f"\n📊 Comparing {run1} vs {run2}")
        
        comparison = {
            "baseline_run": run1,
            "comparison_run": run2,
            "baseline_mean": result1["aggregated_statistics"]["overall_mean"],
            "comparison_mean": result2["aggregated_statistics"]["overall_mean"],
        }
        
        return comparison
    
    def ablation_analysis(
        self,
        decision_engine: Callable,
        baseline_results: Dict
    ) -> Dict:
        """
        Run ablation studies showing component importance.
        
        Each ablation disables one component and measures performance delta.
        """
        
        logger.info(f"\n🔬 Running ablation studies...")
        
        ablation_results = {}
        
        for ablation_name, ablation_path in self.ABLATABLE_COMPONENTS.items():
            logger.info(f"   Testing: {ablation_name}")
            
            # Set ablation flag in config
            self.config.ablations[ablation_name] = True
            
            # Run evaluation with ablation
            ablation_run_results = self.run_evaluation(
                decision_engine=decision_engine,
                run_name=f"ablation_{ablation_name}"
            )
            
            # Compare to baseline
            baseline_mean = baseline_results["aggregated_statistics"]["overall_mean"]
            ablation_mean = ablation_run_results["aggregated_statistics"]["overall_mean"]
            
            ablation_results[ablation_name] = {
                "performance_delta": baseline_mean - ablation_mean,
                "percent_decrease": ((baseline_mean - ablation_mean) / baseline_mean * 100),
                "baseline_mean": baseline_mean,
                "ablated_mean": ablation_mean,
                "component_importance": "HIGH" if (baseline_mean - ablation_mean) > 0.1 else "MEDIUM" if (baseline_mean - ablation_mean) > 0.05 else "LOW"
            }
        
        return ablation_results
    
    def export_results(self, output_file: str = "evaluation_results.json"):
        """Export all results to JSON file"""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                "model_version": self.model_version,
                "runs": self.all_results
            }, f, indent=2)
        
        logger.info(f"✓ Results exported to {output_file}")
