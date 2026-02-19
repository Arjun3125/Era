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
    
    def calibration_diagnostics(
        self,
        predicted_scores: List[float],
        actual_outcomes: List[int],
        n_bins: int = 10
    ) -> Dict:
        """
        Advanced calibration analysis with confidence binning and reliability diagram.
        
        PUBLISHABLE STANDARD: Reliability diagram, ECE, per-bin accuracy.
        
        Args:
            predicted_scores: Model confidence (0-1)
            actual_outcomes: Actual outcomes (0/1)
            n_bins: Number of confidence bins (default 10 for deciles)
        
        Returns:
            Dict with ECE, reliability diagram data, and per-bin metrics
        """
        
        predicted = np.array(predicted_scores)
        actual = np.array(actual_outcomes)
        
        # Create confidence bins
        bin_edges = np.linspace(0, 1.0, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        bin_metrics = []
        total_ece = 0.0
        
        for i in range(n_bins):
            # Get predictions in this bin
            mask = (predicted >= bin_edges[i]) & (predicted < bin_edges[i+1])
            
            if np.sum(mask) == 0:
                # Empty bin
                bin_metrics.append({
                    "bin_center": float(bin_centers[i]),
                    "bin_range": [float(bin_edges[i]), float(bin_edges[i+1])],
                    "count": 0,
                    "avg_confidence": None,
                    "actual_accuracy": None,
                    "calibration_gap": None
                })
                continue
            
            bin_predictions = predicted[mask]
            bin_actual = actual[mask]
            
            avg_confidence = np.mean(bin_predictions)
            actual_accuracy = np.mean(bin_actual)
            calibration_gap = abs(avg_confidence - actual_accuracy)
            
            bin_count = np.sum(mask)
            bin_weight = bin_count / len(actual)
            
            # Weighted ECE contribution
            total_ece += bin_weight * calibration_gap
            
            bin_metrics.append({
                "bin_center": float(bin_centers[i]),
                "bin_range": [float(bin_edges[i]), float(bin_edges[i+1])],
                "count": int(bin_count),
                "avg_confidence": float(avg_confidence),
                "actual_accuracy": float(actual_accuracy),
                "calibration_gap": float(calibration_gap),
                "perfectly_calibrated": abs(calibration_gap) < 0.05
            })
        
        # Interpretation
        if total_ece < 0.05:
            calibration_quality = "EXCELLENT - Well-calibrated confidence"
        elif total_ece < 0.10:
            calibration_quality = "GOOD - Reasonably calibrated"
        elif total_ece < 0.15:
            calibration_quality = "ACCEPTABLE - Slight miscalibration"
        else:
            calibration_quality = "POOR - Significant miscalibration"
        
        return {
            "expected_calibration_error": float(total_ece),
            "calibration_quality": calibration_quality,
            "brier_score": float(np.mean((predicted - actual) ** 2)),
            "n_bins": n_bins,
            "bin_metrics": bin_metrics,
            "overconfident": float(np.mean(predicted)) > float(np.mean(actual)),
            "overconfidence_margin": float(np.mean(predicted) - np.mean(actual)),
            "reliability_diagram_data": {
                "bin_confidences": [m["avg_confidence"] for m in bin_metrics if m["avg_confidence"] is not None],
                "bin_accuracies": [m["actual_accuracy"] for m in bin_metrics if m["actual_accuracy"] is not None],
                "ideal_diagonal": [0.0, 1.0]  # Perfect calibration line
            }
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
    
    def compute_power_analysis(
        self,
        effect_size: float = 0.8,
        alpha: float = 0.05,
        n_seeds: int = 5,
        scenarios_per_seed: int = 20
    ) -> Dict:
        """
        Compute statistical power for paired t-test with given parameters.
        
        Power = Probability of detecting true effect if it exists
        
        Args:
            effect_size: Cohen's d (0.2=small, 0.5=medium, 0.8=large)
            alpha: Significance level (typically 0.05)
            n_seeds: Number of seeds (repeated measures)
            scenarios_per_seed: Scenarios per seed
        
        Returns:
            Dict with power, required_n, and interpretation
        """
        from scipy.stats import nct
        
        n_total = n_seeds * scenarios_per_seed
        
        # For paired t-test: df = n - 1
        df = n_total - 1
        
        # Non-centrality parameter
        # t_critical ≈ 1.96 for α=0.05 (two-tailed)
        t_critical = stats.t.ppf(1 - alpha/2, df)
        
        # Non-centrality parameter λ = effect_size * sqrt(n)
        lambda_nc = effect_size * np.sqrt(n_total)
        
        # Power = P(t > t_critical | λ)
        # Using non-central t distribution
        power = 1 - nct.cdf(t_critical, df, lambda_nc)
        
        # Calculate required sample size for target power
        # Iterative search for n where power >= target (e.g., 0.8)
        target_power = 0.8
        required_n = n_total
        
        for test_n in range(10, 1000):
            test_df = test_n - 1
            test_t_critical = stats.t.ppf(1 - alpha/2, test_df)
            test_lambda = effect_size * np.sqrt(test_n)
            test_power = 1 - nct.cdf(test_t_critical, test_df, test_lambda)
            
            if test_power >= target_power:
                required_n = test_n
                break
        
        # Interpretation
        if power >= 0.90:
            power_interpretation = "EXCELLENT - High probability of detecting effect"
        elif power >= 0.80:
            power_interpretation = "GOOD - Standard statistical power"
        elif power >= 0.70:
            power_interpretation = "ACCEPTABLE - Moderate probability of detection"
        else:
            power_interpretation = "INSUFFICIENT - Risk of Type II error (false negative)"
        
        return {
            "effect_size": effect_size,
            "effect_size_interpretation": {
                0.2: "small",
                0.5: "medium",
                0.8: "large"
            }.get(effect_size, "custom"),
            "alpha": alpha,
            "n_total": n_total,
            "n_seeds": n_seeds,
            "scenarios_per_seed": scenarios_per_seed,
            "statistical_power": float(power),
            "power_interpretation": power_interpretation,
            "required_n_for_80_power": required_n,
            "required_scenario_increase": max(0, required_n - n_total),
            "is_adequately_powered": power >= 0.80
        }
    
    def power_grid_analysis(self) -> Dict:
        """
        Generate power analysis grid across common effect sizes.
        
        Helps determine if 100 scenarios (5 seeds × 20 scenarios) is sufficient.
        
        Returns:
            Grid of power values for different effect sizes
        """
        
        effect_sizes = [0.2, 0.5, 0.8, 1.0, 1.2]
        n_total = 100  # 5 seeds × 20 scenarios
        
        grid = {}
        
        for es in effect_sizes:
            analysis = self.compute_power_analysis(
                effect_size=es,
                alpha=0.05,
                n_seeds=5,
                scenarios_per_seed=20
            )
            grid[es] = {
                "power": analysis["statistical_power"],
                "interpretation": analysis["power_interpretation"],
                "adequately_powered": analysis["is_adequately_powered"]
            }
        
        return {
            "n_total": n_total,
            "power_grid": grid,
            "recommendation": self._interpret_power_grid(grid)
        }
    
    def _interpret_power_grid(self, grid: Dict) -> str:
        """Interpret power grid and provide recommendation."""
        
        # Check worst case (smallest effect size)
        if grid[0.2]["adequately_powered"]:
            return "✅ EXCELLENT: Powered to detect even small effects"
        elif grid[0.5]["adequately_powered"]:
            return "✅ GOOD: Powered to detect medium effects (most relevant)"
        elif grid[0.8]["adequately_powered"]:
            return "✓ ACCEPTABLE: Powered for large effects, may miss medium effects"
        else:
            return "⚠️  UNDERPOWERED: Consider increasing sample size"
