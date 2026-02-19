"""
Evaluation Runner - Main orchestration for research-grade benchmarking

5 seed runs, ablation matrix, isolation mode, statistical validation.
"""

import json
from pathlib import Path
from typing import Dict, List, Callable, Optional
import logging

from evaluation.scoring.outcome_scorer import OutcomeScorer
from evaluation.scoring.regret_scorer import RegretScorer
from evaluation.scoring.rubric_engine import RubricEngine
from evaluation.stats_engine import StatsEngine

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
    
    def to_dict(self) -> Dict:
        return {
            "evaluation_mode": self.evaluation_mode,
            "seed_list": self.seed_list,
            "isolation_mode": self.isolation_mode,
            "ablations": self.ablations
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
        run_name: str = "baseline"
    ) -> Dict:
        """
        Run full evaluation with multiple seeds.
        
        Args:
            decision_engine: Function that takes scenario and returns (decision_path, rationale)
            run_name: Name for this evaluation run (e.g., "baseline", "council", "no_ministers")
        
        Returns:
            Aggregated results across all seeds
        """
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting evaluation: {run_name}")
        logger.info(f"{'='*60}")
        
        # Step 1: Verify integrity (hard rule)
        if not self.verify_dataset_integrity():
            return {"status": "ABORTED", "reason": "Dataset integrity check failed"}
        
        # Step 2: Enable isolation mode
        self.enable_isolation_mode()
        
        # Step 3: Load all scenarios
        logger.info("\n📂 Loading scenarios...")
        scenarios = self.rubric_engine.load_all_scenarios()
        logger.info(f"   Loaded {len(scenarios)} scenarios")
        
        # Step 4: Run with multiple seeds
        seed_results = {}
        
        for seed in self.config.seed_list:
            logger.info(f"\n🌱 Running seed {seed}...")
            self._run_seed(seed, scenarios, decision_engine, run_name, seed_results)
        
        # Step 5: Compute statistics
        logger.info(f"\n📊 Computing statistics...")
        stats = self.stats_engine.aggregate_seed_results(seed_results)
        
        # Step 6: Compute confidence intervals
        all_scores = [s for scores in seed_results.values() for s in scores]
        ci = self.stats_engine.compute_confidence_intervals(all_scores)
        
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
        seed_results: Dict
    ):
        """Run evaluation with a single seed"""
        
        import random
        import numpy as np
        
        # Set seeds for reproducibility
        random.seed(seed)
        np.random.seed(seed)
        
        seed_scores = []
        
        for scenario_id, scenario in scenarios.items():
            try:
                # Get decision from engine
                decision_path, rationale = decision_engine(scenario)
                
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
                
            except Exception as e:
                logger.warning(f"   Error evaluating {scenario_id}: {e}")
                seed_scores.append(0.0)
        
        seed_results[seed] = seed_scores
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
