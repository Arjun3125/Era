"""
Statistics Engine - Computes statistical validation metrics

Five seed runs, bootstrap resampling, paired t-tests, effect sizes,
calibration curves. Research-grade statistical rigor.
"""

import numpy as np
from typing import List, Dict, Tuple
from scipy import stats
from dataclasses import dataclass, asdict


@dataclass
class ConfidenceInterval:
    """95% confidence interval with effect size"""
    mean: float
    lower: float
    upper: float
    std_error: float
    effect_size: float  # Cohen's d
    

class StatsEngine:
    """Compute statistical validation metrics for evaluations"""
    
    def __init__(self, n_seeds: int = 5, n_bootstrap: int = 1000):
        self.n_seeds = n_seeds
        self.n_bootstrap = n_bootstrap
        self.baseline_scores = None
        self.council_scores = None
    
    def compute_confidence_intervals(self, scores: List[float]) -> ConfidenceInterval:
        """
        Compute 95% CI using bootstrap resampling.
        
        Args:
            scores: List of outcome scores (0.0-1.0)
        
        Returns:
            ConfidenceInterval with mean, bounds, and effect size
        """
        
        scores = np.array(scores)
        mean = np.mean(scores)
        
        # Bootstrap resampling
        bootstrap_means = []
        for _ in range(self.n_bootstrap):
            sample = np.random.choice(scores, size=len(scores), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        bootstrap_means = np.array(bootstrap_means)
        lower = np.percentile(bootstrap_means, 2.5)
        upper = np.percentile(bootstrap_means, 97.5)
        std_error = np.std(bootstrap_means)
        
        # Cohen's d (effect size)
        cohens_d = (mean - 0.5) / np.std(scores) if np.std(scores) > 0 else 0
        
        return ConfidenceInterval(
            mean=float(mean),
            lower=float(lower),
            upper=float(upper),
            std_error=float(std_error),
            effect_size=float(cohens_d)
        )
    
    def paired_t_test(
        self,
        baseline_scores: List[float],
        council_scores: List[float]
    ) -> Dict:
        """
        Paired t-test comparing baseline vs council approach.
        
        Returns:
            Dict with t-statistic, p-value, effect size
        """
        
        baseline = np.array(baseline_scores)
        council = np.array(council_scores)
        
        if len(baseline) != len(council):
            raise ValueError("Baseline and council scores must have same length")
        
        # Paired t-test
        t_stat, p_value = stats.ttest_rel(council, baseline)
        
        # Effect size (Cohen's d for paired samples)
        diff = council - baseline
        cohens_d = np.mean(diff) / np.std(diff) if np.std(diff) > 0 else 0
        
        return {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "significant_at_005": float(p_value) < 0.05,
            "cohens_d": float(cohens_d),
            "mean_difference": float(np.mean(diff)),
            "baseline_mean": float(np.mean(baseline)),
            "council_mean": float(np.mean(council))
        }
    
    def bootstrap_paired_test(
        self,
        baseline_scores: List[float],
        council_scores: List[float]
    ) -> Dict:
        """
        Bootstrap-based paired test (non-parametric alternative).
        """
        
        baseline = np.array(baseline_scores)
        council = np.array(council_scores)
        diff = council - baseline
        
        # Bootstrap resampling of differences
        bootstrap_means = []
        for _ in range(self.n_bootstrap):
            sample = np.random.choice(diff, size=len(diff), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        bootstrap_means = np.array(bootstrap_means)
        
        # p-value: proportion of bootstrap samples with opposite sign
        p_value = np.mean(bootstrap_means < 0) if np.mean(diff) > 0 else np.mean(bootstrap_means > 0)
        p_value = min(p_value, 1 - p_value) * 2  # Two-tailed
        
        return {
            "bootstrap_mean_diff": float(np.mean(bootstrap_means)),
            "ci_lower": float(np.percentile(bootstrap_means, 2.5)),
            "ci_upper": float(np.percentile(bootstrap_means, 97.5)),
            "p_value_bootstrap": float(p_value),
            "significant_at_005": float(p_value) < 0.05
        }
    
    def calibration_curve(self, predicted_scores: List[float], actual_outcomes: List[int]) -> Dict:
        """
        Compute calibration error (Brier score).
        
        Brier score = mean squared error between predicted and actual.
        Lower is better (0 = perfect, 1 = worst).
        
        Args:
            predicted_scores: Model confidence scores (0-1)
            actual_outcomes: Actual binary outcomes (0 or 1)
        
        Returns:
            Dict with Brier score and reliability metrics
        """
        
        predicted = np.array(predicted_scores)
        actual = np.array(actual_outcomes)
        
        # Brier score
        brier = np.mean((predicted - actual) ** 2)
        
        # Reliability: are high-confidence predictions actually correct?
        high_conf = predicted > 0.7
        if np.sum(high_conf) > 0:
            high_conf_accuracy = np.mean(actual[high_conf])
        else:
            high_conf_accuracy = 0
        
        low_conf = predicted < 0.3
        if np.sum(low_conf) > 0:
            low_conf_accuracy = np.mean(actual[low_conf])
        else:
            low_conf_accuracy = 0
        
        return {
            "brier_score": float(brier),
            "calibration_error": float(abs(high_conf_accuracy - 0.7)),
            "high_confidence_accuracy": float(high_conf_accuracy) if np.sum(high_conf) > 0 else None,
            "low_confidence_accuracy": float(low_conf_accuracy) if np.sum(low_conf) > 0 else None
        }
    
    def ablation_effect_size(self, baseline_scores: List[float], ablated_scores: List[float]) -> Dict:
        """
        Compute effect size delta for an ablation.
        
        How much does performance drop when a component is removed?
        """
        
        baseline = np.array(baseline_scores)
        ablated = np.array(ablated_scores)
        
        baseline_mean = np.mean(baseline)
        ablated_mean = np.mean(ablated)
        pooled_std = np.sqrt((np.std(baseline) ** 2 + np.std(ablated) ** 2) / 2)
        
        cohens_d = (baseline_mean - ablated_mean) / pooled_std if pooled_std > 0 else 0
        
        return {
            "performance_delta": float(baseline_mean - ablated_mean),
            "baseline_mean": float(baseline_mean),
            "ablated_mean": float(ablated_mean),
            "cohens_d": float(cohens_d),
            "percent_decrease": float((baseline_mean - ablated_mean) / baseline_mean * 100) if baseline_mean > 0 else 0
        }
    
    def aggregate_seed_results(self, seed_results: Dict[int, List[float]]) -> Dict:
        """
        Aggregate results from multiple seed runs.
        
        Args:
            seed_results: {seed_num: [scores], ...}
        
        Returns:
            Aggregated statistics across seeds
        """
        
        all_scores = []
        seed_means = []
        
        for seed, scores in seed_results.items():
            all_scores.extend(scores)
            seed_means.append(np.mean(scores))
        
        seed_means = np.array(seed_means)
        
        return {
            "overall_mean": float(np.mean(all_scores)),
            "seed_mean_std": float(np.std(seed_means)),
            "seed_consistency": "high" if np.std(seed_means) < 0.05 else "moderate" if np.std(seed_means) < 0.1 else "low",
            "n_seeds": len(seed_results),
            "n_total_scenarios": len(all_scores)
        }
