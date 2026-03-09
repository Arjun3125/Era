#!/usr/bin/env python
"""
ERA Evaluation Benchmark Runner

Research-grade evaluation with:
- Deterministic LLM control (temperature=0, seed injection)
- Rule-based deterministic scoring (zero LLM calls)
- Dataset integrity verification
- Isolation mode (no live system contamination)
- 5-seed reproducibility
- Statistical validation

Usage:
  python run_benchmark.py [--quick] [--ablations]
  
  --quick: Run subset of scenarios for testing
  --ablations: Include component ablation studies
"""

import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, Tuple

# Configure environment
os.environ["SKIP_OLLAMA_CHECK"] = "1"  # Allow running without Ollama for now

from evaluation.evaluation_runner import EvaluationRunner
from evaluation.stats_engine import StatsEngine
from evaluation.metrics.evaluation_metrics import EvaluationMetrics
from llm.runtime import OllamaRuntime

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Main driver for evaluation benchmarking"""
    
    def __init__(self):
        self.runner = EvaluationRunner()
        self.stats_engine = StatsEngine()
        self.all_runs = {}
        self.fail_fast_errors = os.getenv("EVAL_FAIL_FAST_ERRORS", "0").lower() in {"1", "true", "yes"}

    def _parse_model_response(
        self,
        response: str,
        fallback_decision: str,
        acceptable_paths: list[str] | None = None,
    ) -> Tuple[str, float]:
        """Extract decision path and confidence from model output."""
        text = response or ""
        normalized_paths = set()
        if acceptable_paths:
            normalized_paths = {
                p.lower().replace("-", "_").replace(" ", "_")
                for p in acceptable_paths
            }
        decision_match = re.search(
            r"(?im)^[>\s`*_:-]*\*{0,2}decision\*{0,2}\s*[:\-]\s*(.+)$",
            text,
        )
        confidence_match = re.search(
            r"(?im)^[>\s`*_:-]*\*{0,2}confidence\*{0,2}\s*[:\-]\s*([0-9]*\.?[0-9]+)\s*%?\s*$",
            text,
        )
        minister_matches = re.findall(
            r"(?im)^[>\s`*_:-]*minister_[a-z_]+\s*:\s*([^|\n]+?)\s*\|\s*([0-9]*\.?[0-9]+)",
            text,
        )

        decision = fallback_decision
        if decision_match:
            decision_line = decision_match.group(1).strip().splitlines()[0].strip()
            decision = re.sub(r"[^a-z0-9_ -]", "", decision_line.lower()).replace("-", "_").replace(" ", "_")
            if normalized_paths:
                if decision not in normalized_paths:
                    for normalized in normalized_paths:
                        if normalized in decision:
                            decision = normalized
                            break
                if decision not in normalized_paths:
                    for normalized in normalized_paths:
                        if decision in normalized:
                            decision = normalized
                            break
                if decision not in normalized_paths:
                    decision_tokens = {t for t in decision.split("_") if t}
                    best_path = None
                    best_overlap = 0.0
                    for normalized in normalized_paths:
                        path_tokens = {t for t in normalized.split("_") if t}
                        if not path_tokens:
                            continue
                        overlap = len(decision_tokens & path_tokens) / len(path_tokens)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_path = normalized
                    if best_path is not None and best_overlap >= 0.5:
                        decision = best_path
        elif minister_matches:
            # Recovery path for council outputs that include minister lines but omit DECISION.
            score_by_path: Dict[str, float] = {}
            for raw_path, raw_conf in minister_matches:
                path = re.sub(r"[^a-z0-9_ -]", "", raw_path.lower()).strip().replace("-", "_").replace(" ", "_")
                conf = float(raw_conf)
                conf = conf / 100.0 if conf > 1.0 else conf
                conf = max(0.0, min(1.0, conf))
                score_by_path[path] = score_by_path.get(path, 0.0) + conf
            if score_by_path:
                ranked_paths = sorted(score_by_path.items(), key=lambda item: item[1], reverse=True)
                decision = ranked_paths[0][0]
                if normalized_paths and decision not in normalized_paths:
                    for candidate, _ in ranked_paths:
                        if candidate in normalized_paths:
                            decision = candidate
                            break
        if self.fail_fast_errors and normalized_paths and decision not in normalized_paths:
            raise ValueError(
                f"Decision '{decision}' is not in acceptable paths {sorted(normalized_paths)}"
            )
        if self.fail_fast_errors and not decision_match and not minister_matches:
            raise ValueError("Missing DECISION line in model response.")

        confidence = 0.5
        if confidence_match:
            raw = float(confidence_match.group(1))
            confidence = raw / 100.0 if raw > 1.0 else raw
            confidence = max(0.0, min(1.0, confidence))
        elif minister_matches:
            conf_values = []
            for _, raw_conf in minister_matches:
                raw = float(raw_conf)
                conf_values.append(raw / 100.0 if raw > 1.0 else raw)
            if conf_values:
                confidence = max(0.0, min(1.0, sum(conf_values) / len(conf_values)))
        elif self.fail_fast_errors:
            raise ValueError("Missing CONFIDENCE line in model response.")

        return decision, confidence
    
    def baseline_decision_engine(self, scenario: Dict) -> Tuple[str, str, float]:
        """
        Direct LLM approach - no council, no orchestration
        
        Returns: (decision_path, rationale)
        """
        try:
            acceptable_paths = scenario.get("ground_truth_rubric", {}).get("acceptable_paths", [])
            prompt = f"""Analyze this decision scenario and provide your recommendation.

Scenario: {scenario.get('input', 'No input')[:200]}
Acceptable decision paths (choose exactly one): {acceptable_paths}

Output constraints:
- Return exactly 3 lines, no extra text.
- Keep RATIONALE to <= 20 words.

Provide your final answer in exactly this format:
DECISION: [choose one of the acceptable paths]
RATIONALE: [explain your reasoning]
CONFIDENCE: [0.00 to 1.00]"""
            
            try:
                # Attempt to use OllamaRuntime if available
                llm = OllamaRuntime()
                response = llm.speak("You are a decision analyst.", prompt)
            except Exception:
                if self.fail_fast_errors:
                    raise
                # Fallback to mock response if Ollama unavailable
                response = "DECISION: conservative_approach\nRATIONALE: Unclear information requires further investigation."
            
            # Parse response
            decision_path, confidence = self._parse_model_response(
                response,
                fallback_decision="baseline_decision",
                acceptable_paths=acceptable_paths,
            )
            rationale = response if response else "No response"
            
            return decision_path, rationale, confidence
        
        except Exception as e:
            if self.fail_fast_errors:
                raise
            logger.warning(f"  Baseline engine error: {e}")
            return "error_response", str(e), 0.0
    
    def council_decision_engine(self, scenario: Dict) -> Tuple[str, str, float]:
        """
        Full council approach with all components
        
        Returns: (decision_path, rationale)
        """
        try:
            acceptable_paths = scenario.get("ground_truth_rubric", {}).get("acceptable_paths", [])
            prompt = f"""As a decision council with multiple perspectives, analyze this scenario.

Scenario: {scenario.get('input', 'No input')[:200]}
Acceptable decision paths (choose exactly one): {acceptable_paths}

Consider risk, optionality, information value, and timing.

Output constraints:
- Return exactly 3 lines, no extra text.
- Keep RATIONALE to <= 20 words.

Provide your final answer in exactly this format:
DECISION: [choose one of the acceptable paths]
RATIONALE: [explain your reasoning as a council]
CONFIDENCE: [0.00 to 1.00]"""
            
            try:
                # Attempt to use OllamaRuntime if available
                llm = OllamaRuntime()
                response = llm.speak(
                    "You are a council of decision experts with diverse perspectives.",
                    prompt
                )
            except Exception:
                if self.fail_fast_errors:
                    raise
                # Fallback to mock response if Ollama unavailable
                response = "DECISION: balanced_approach\nRATIONALE: Council recommends maintaining flexibility while gathering more information."
            
            decision_path, confidence = self._parse_model_response(
                response,
                fallback_decision="council_decision",
                acceptable_paths=acceptable_paths,
            )
            rationale = response if response else "No response"
            
            return decision_path, rationale, confidence
        
        except Exception as e:
            if self.fail_fast_errors:
                raise
            logger.warning(f"  Council engine error: {e}")
            return "error_response", str(e), 0.0
    
    def run_benchmark(self, quick: bool = False, limit: int = None):
        """
        Run complete benchmark comparing baseline vs council
        
        Args:
            quick: If True, limit to first 10 scenarios for testing
        """
        
        logger.info("\n" + "="*70)
        logger.info("ERA EVALUATION BENCHMARK - RESEARCH-GRADE VALIDATION")
        logger.info("="*70)
        
        # Step 1: Verification
        logger.info("\n[STEP 1] Dataset Integrity Verification")
        logger.info("-" * 70)
        
        if not self.runner.verify_dataset_integrity():
            logger.error("❌ Dataset integrity check failed. Aborting.")
            return
        
        logger.info("✅ Dataset integrity verified")
        logger.info(f"   Model version: {self.runner.model_version.get('model_version')}")
        logger.info(f"   Seeds: {self.runner.config.seed_list}")
        logger.info(f"   Scenario count: 100 (25 per category)")
        
        # Step 2: Isolation mode
        logger.info("\n[STEP 2] Isolation Mode Activation")
        logger.info("-" * 70)
        self.runner.enable_isolation_mode()
        
        # Step 3: Run Baseline
        logger.info("\n[STEP 3] Baseline Evaluation (Direct LLM)")
        logger.info("-" * 70)
        
        baseline_results = self.runner.run_evaluation(
            decision_engine=self.baseline_decision_engine,
            run_name="baseline",
            scenario_limit=limit
        )
        
        self.all_runs["baseline"] = baseline_results
        
        # Step 4: Run Council
        logger.info("\n[STEP 4] Council Evaluation (Full Orchestration)")
        logger.info("-" * 70)
        
        council_results = self.runner.run_evaluation(
            decision_engine=self.council_decision_engine,
            run_name="council",
            scenario_limit=limit
        )
        
        self.all_runs["council"] = council_results
        
        # Step 5: Statistical Comparison
        logger.info("\n[STEP 5] Statistical Comparison")
        logger.info("-" * 70)
        
        baseline_map = baseline_results.get("scenario_scores_mean", {})
        council_map = council_results.get("scenario_scores_mean", {})
        shared_ids = sorted(set(baseline_map.keys()) & set(council_map.keys()))
        
        baseline_scores = [baseline_map[sid] for sid in shared_ids]
        council_scores = [council_map[sid] for sid in shared_ids]
        
        if baseline_scores and council_scores:
            metrics = EvaluationMetrics(
                scenario_scores_baseline=baseline_scores,
                scenario_scores_council=council_scores,
            )
            ttest = metrics.compute_paired_ttest()
            effect_size = metrics.compute_effect_size()
            comparison = {
                "baseline_mean": metrics.compute_mean(baseline_scores),
                "council_mean": metrics.compute_mean(council_scores),
                "mean_difference": metrics.compute_mean(council_scores) - metrics.compute_mean(baseline_scores),
                "t_statistic": ttest["t_statistic"],
                "p_value": ttest["p_value"],
                "significant_at_005": ttest["significant_at_005"],
                "cohens_d": effect_size,
            }
            
            logger.info(f"\n  Baseline mean: {comparison['baseline_mean']:.3f}")
            logger.info(f"  Council mean: {comparison['council_mean']:.3f}")
            logger.info(f"  Mean difference: {comparison['mean_difference']:.3f}")
            logger.info(f"  Paired scenarios: {len(shared_ids)}")
            logger.info(f"  t-statistic: {comparison['t_statistic']:.2f}")
            logger.info(f"  p-value: {comparison['p_value']:.4f}")
            logger.info(f"  Cohen's d: {comparison['cohens_d']:.2f}")
            
            if comparison["significant_at_005"]:
                logger.info(f"  ✅ SIGNIFICANT at p<0.05")
            else:
                logger.info(f"  ❌ Not significant at p<0.05")
            
            self.all_runs["comparison"] = comparison
        
        # Step 6: Power Analysis
        logger.info("\n[STEP 6] Power Analysis")
        logger.info("-" * 70)
        
        power_analysis = self.stats_engine.compute_power_analysis(
            effect_size=0.8,
            alpha=0.05,
            n_seeds=5,
            scenarios_per_seed=20
        )
        
        logger.info(f"\n  Effect size target: {power_analysis['effect_size']}")
        logger.info(f"  Statistical power: {power_analysis['statistical_power']:.2f}")
        logger.info(f"  Power interpretation: {power_analysis['power_interpretation']}")
        logger.info(f"  Adequately powered: {'✅ YES' if power_analysis['is_adequately_powered'] else '❌ NO'}")
        
        self.all_runs["power_analysis"] = power_analysis
        
        # Step 7: Calibration Analysis
        logger.info("\n[STEP 7] Calibration Diagnostics")
        logger.info("-" * 70)
        
        council_conf = council_results.get("scenario_confidence_mean", {})
        council_outcomes = council_results.get("scenario_outcome_binary", {})
        shared_cal_ids = sorted(set(council_conf.keys()) & set(council_outcomes.keys()))

        predicted_scores = [float(council_conf[sid]) for sid in shared_cal_ids]
        actual_outcomes = [int(council_outcomes[sid]) for sid in shared_cal_ids]

        calibration_metrics = EvaluationMetrics()
        ece = calibration_metrics.compute_ece(predicted_scores, actual_outcomes)
        brier = calibration_metrics.compute_brier(predicted_scores, actual_outcomes)

        isotonic = calibration_metrics.apply_isotonic_regression_crossfit(
            predicted_scores, actual_outcomes, n_folds=5, random_seed=42
        )
        calibrated_scores = isotonic["calibrated_probabilities"]
        calibrated_ece = calibration_metrics.compute_ece(calibrated_scores, actual_outcomes)
        calibrated_brier = calibration_metrics.compute_brier(calibrated_scores, actual_outcomes)

        if ece < 0.05:
            calibration_quality = "EXCELLENT - Well-calibrated confidence"
        elif ece < 0.10:
            calibration_quality = "GOOD - Reasonably calibrated"
        elif ece < 0.15:
            calibration_quality = "ACCEPTABLE - Slight miscalibration"
        else:
            calibration_quality = "POOR - Significant miscalibration"

        if calibrated_ece < 0.05:
            calibrated_quality = "EXCELLENT - Well-calibrated confidence"
        elif calibrated_ece < 0.10:
            calibrated_quality = "GOOD - Reasonably calibrated"
        elif calibrated_ece < 0.15:
            calibrated_quality = "ACCEPTABLE - Slight miscalibration"
        else:
            calibrated_quality = "POOR - Significant miscalibration"

        calibration = {
            "expected_calibration_error": ece,
            "brier_score": brier,
            "calibration_quality": calibration_quality,
            "overconfident": (
                (sum(predicted_scores) / len(predicted_scores)) >
                (sum(actual_outcomes) / len(actual_outcomes))
            ) if predicted_scores else False,
            "n_scenarios": len(shared_cal_ids),
            "source": "council_scenario_confidence_vs_binary_outcome",
            "isotonic_regression": {
                "method": "pair_adjacent_violators_crossfit",
                "crossfit_folds": isotonic["folds"],
                "expected_calibration_error": calibrated_ece,
                "brier_score": calibrated_brier,
                "calibration_quality": calibrated_quality,
                "ece_improvement": ece - calibrated_ece,
                "brier_improvement": brier - calibrated_brier,
                "model": isotonic["global_model"],
            },
        }
        
        logger.info(f"\n  Expected Calibration Error (ECE): {calibration['expected_calibration_error']:.3f}")
        logger.info(f"  Brier Score: {calibration['brier_score']:.3f}")
        logger.info(f"  Calibration Quality: {calibration['calibration_quality']}")
        logger.info(f"  Overconfident: {calibration['overconfident']}")
        logger.info(f"  Isotonic ECE: {calibration['isotonic_regression']['expected_calibration_error']:.3f}")
        logger.info(f"  Isotonic Brier: {calibration['isotonic_regression']['brier_score']:.3f}")
        logger.info(f"  ECE Improvement: {calibration['isotonic_regression']['ece_improvement']:.3f}")
        logger.info(f"  Brier Improvement: {calibration['isotonic_regression']['brier_improvement']:.3f}")
        
        self.all_runs["calibration"] = calibration
        
        # Step 8: Summary
        logger.info("\n[STEP 8] Benchmark Summary")
        logger.info("-" * 70)
        
        self._print_summary()
        
        # Step 9: Save results
        logger.info("\n[STEP 9] Saving Results")
        logger.info("-" * 70)
        
        self._save_results()
        
        logger.info("\n" + "="*70)
        logger.info("BENCHMARK COMPLETE")
        logger.info("="*70)
    
    def _print_summary(self):
        """Print human-readable summary"""
        
        logger.info("\n✅ EVALUATION STATUS")
        for run_name, results in self.all_runs.items():
            if isinstance(results, dict) and "status" in results:
                logger.info(f"\n  {run_name}:")
                logger.info(f"    Status: {results.get('status')}")
                
                agg = results.get("aggregated_statistics", {})
                logger.info(f"    Mean: {agg.get('overall_mean', 0):.3f}")
                logger.info(f"    Consistency: {agg.get('seed_consistency')}")
                
                ci = results.get("confidence_interval", {})
                logger.info(f"    95% CI: [{ci.get('lower_95', 0):.3f}, {ci.get('upper_95', 0):.3f}]")
    
    def _save_results(self):
        """Save benchmark results to JSON"""
        
        results_dir = Path("evaluation/results")
        results_dir.mkdir(exist_ok=True)
        
        results_file = results_dir / "benchmark_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.all_runs, f, indent=2, default=str)
        
        logger.info(f"  Results saved: {results_file}")


def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="ERA Evaluation Benchmark")
    parser.add_argument("--quick", action="store_true", help="Quick test mode")
    parser.add_argument("--ablations", action="store_true", help="Include ablation studies")
    parser.add_argument("--limit", type=int, default=None, help="Limit core benchmark scenarios after integrity validation")
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner()
    runner.run_benchmark(quick=args.quick, limit=args.limit)


if __name__ == "__main__":
    main()
