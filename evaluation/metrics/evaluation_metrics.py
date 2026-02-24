"""Detached evaluation metrics for frozen benchmark analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np
from scipy import stats


@dataclass
class EvaluationMetrics:
    """Evaluation-only metrics container (never touches live system metrics)."""

    scenario_scores_baseline: List[float] = field(default_factory=list)
    scenario_scores_council: List[float] = field(default_factory=list)

    def compute_mean(self, scores: Sequence[float]) -> float:
        if not scores:
            return 0.0
        return float(np.mean(np.asarray(scores, dtype=float)))

    def compute_variance(self, scores: Sequence[float]) -> float:
        if not scores:
            return 0.0
        return float(np.var(np.asarray(scores, dtype=float)))

    def compute_bootstrap_ci(
        self,
        scores: Sequence[float],
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
    ) -> Dict[str, float]:
        if not scores:
            return {"mean": 0.0, "lower": 0.0, "upper": 0.0}

        arr = np.asarray(scores, dtype=float)
        means = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(arr, size=len(arr), replace=True)
            means.append(float(np.mean(sample)))

        alpha = 1.0 - confidence
        lower = float(np.percentile(means, alpha / 2 * 100.0))
        upper = float(np.percentile(means, (1.0 - alpha / 2) * 100.0))
        return {"mean": float(np.mean(arr)), "lower": lower, "upper": upper}

    def compute_paired_ttest(self) -> Dict[str, float | bool]:
        if len(self.scenario_scores_baseline) != len(self.scenario_scores_council):
            raise ValueError("Baseline and council score lists must have equal length")
        if not self.scenario_scores_baseline:
            return {
                "t_statistic": 0.0,
                "p_value": 1.0,
                "significant_at_005": False,
            }

        baseline = np.asarray(self.scenario_scores_baseline, dtype=float)
        council = np.asarray(self.scenario_scores_council, dtype=float)
        t_stat, p_value = stats.ttest_rel(council, baseline)
        return {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "significant_at_005": bool(p_value < 0.05),
        }

    def compute_effect_size(self) -> float:
        if len(self.scenario_scores_baseline) != len(self.scenario_scores_council):
            raise ValueError("Baseline and council score lists must have equal length")
        if not self.scenario_scores_baseline:
            return 0.0

        diff = np.asarray(self.scenario_scores_council, dtype=float) - np.asarray(
            self.scenario_scores_baseline, dtype=float
        )
        std = float(np.std(diff))
        if std == 0.0:
            return 0.0
        return float(np.mean(diff) / std)

    def compute_brier(
        self,
        predicted_probabilities: Sequence[float],
        actual_outcomes: Sequence[int],
    ) -> float:
        if len(predicted_probabilities) != len(actual_outcomes):
            raise ValueError("Predictions and outcomes must have equal length")
        if not predicted_probabilities:
            return 0.0

        pred = np.asarray(predicted_probabilities, dtype=float)
        actual = np.asarray(actual_outcomes, dtype=float)
        return float(np.mean((pred - actual) ** 2))

    def compute_ece(
        self,
        predicted_probabilities: Sequence[float],
        actual_outcomes: Sequence[int],
        n_bins: int = 10,
    ) -> float:
        if len(predicted_probabilities) != len(actual_outcomes):
            raise ValueError("Predictions and outcomes must have equal length")
        if not predicted_probabilities:
            return 0.0

        pred = np.asarray(predicted_probabilities, dtype=float)
        actual = np.asarray(actual_outcomes, dtype=float)
        edges = np.linspace(0.0, 1.0, n_bins + 1)

        ece = 0.0
        for i in range(n_bins):
            in_bin = (pred >= edges[i]) & (pred < edges[i + 1])
            count = int(np.sum(in_bin))
            if count == 0:
                continue
            conf = float(np.mean(pred[in_bin]))
            acc = float(np.mean(actual[in_bin]))
            ece += (count / len(pred)) * abs(conf - acc)
        return float(ece)

    def apply_isotonic_regression(
        self,
        predicted_probabilities: Sequence[float],
        actual_outcomes: Sequence[int],
    ) -> Dict[str, List[float] | Dict[str, List[float]]]:
        """
        Fit isotonic regression with a pair-adjacent-violators (PAV) solver and
        return calibrated probabilities for the same inputs.
        """
        if len(predicted_probabilities) != len(actual_outcomes):
            raise ValueError("Predictions and outcomes must have equal length")
        if len(predicted_probabilities) == 0:
            return {
                "calibrated_probabilities": [],
                "model": {"x_thresholds": [], "y_thresholds": []},
            }

        pred = np.asarray(predicted_probabilities, dtype=float)
        actual = np.asarray(actual_outcomes, dtype=float)
        pred = np.clip(pred, 0.0, 1.0)
        actual = np.clip(actual, 0.0, 1.0)

        sort_idx = np.argsort(pred, kind="mergesort")
        x_sorted = pred[sort_idx]
        y_sorted = actual[sort_idx]

        # Compress equal x values to weighted points.
        unique_x = []
        unique_y = []
        unique_w = []
        for x, y in zip(x_sorted, y_sorted):
            if unique_x and x == unique_x[-1]:
                w_prev = unique_w[-1]
                unique_w[-1] = w_prev + 1.0
                unique_y[-1] = (unique_y[-1] * w_prev + y) / unique_w[-1]
            else:
                unique_x.append(float(x))
                unique_y.append(float(y))
                unique_w.append(1.0)

        block_y = unique_y[:]
        block_w = unique_w[:]
        block_start = list(range(len(unique_x)))
        block_end = list(range(len(unique_x)))

        i = 0
        while i < len(block_y) - 1:
            if block_y[i] > block_y[i + 1]:
                merged_w = block_w[i] + block_w[i + 1]
                merged_y = (block_y[i] * block_w[i] + block_y[i + 1] * block_w[i + 1]) / merged_w

                block_y[i] = float(merged_y)
                block_w[i] = float(merged_w)
                block_end[i] = block_end[i + 1]

                del block_y[i + 1]
                del block_w[i + 1]
                del block_start[i + 1]
                del block_end[i + 1]

                if i > 0:
                    i -= 1
            else:
                i += 1

        y_thresholds = np.empty(len(unique_x), dtype=float)
        for s, e, y in zip(block_start, block_end, block_y):
            y_thresholds[s : e + 1] = y

        x_thresholds = np.asarray(unique_x, dtype=float)

        calibrated_sorted = np.interp(x_sorted, x_thresholds, y_thresholds)
        calibrated = np.empty_like(calibrated_sorted)
        calibrated[sort_idx] = calibrated_sorted
        calibrated = np.clip(calibrated, 0.0, 1.0)

        return {
            "calibrated_probabilities": calibrated.tolist(),
            "model": {
                "x_thresholds": x_thresholds.tolist(),
                "y_thresholds": y_thresholds.tolist(),
            },
        }

    def apply_isotonic_regression_crossfit(
        self,
        predicted_probabilities: Sequence[float],
        actual_outcomes: Sequence[int],
        n_folds: int = 5,
        random_seed: int = 42,
    ) -> Dict[str, List[float] | Dict[str, List[float]]]:
        """
        Cross-fitted isotonic regression to avoid optimistic in-sample calibration.
        """
        if len(predicted_probabilities) != len(actual_outcomes):
            raise ValueError("Predictions and outcomes must have equal length")
        if not predicted_probabilities:
            return {
                "calibrated_probabilities": [],
                "global_model": {"x_thresholds": [], "y_thresholds": []},
                "folds": 0,
            }

        n = len(predicted_probabilities)
        folds = max(2, min(int(n_folds), n))
        rng = np.random.default_rng(random_seed)
        idx = np.arange(n)
        rng.shuffle(idx)
        fold_splits = np.array_split(idx, folds)

        pred = np.asarray(predicted_probabilities, dtype=float)
        actual = np.asarray(actual_outcomes, dtype=float)
        calibrated = np.zeros(n, dtype=float)

        for test_idx in fold_splits:
            train_mask = np.ones(n, dtype=bool)
            train_mask[test_idx] = False
            train_idx = np.where(train_mask)[0]

            fitted = self.apply_isotonic_regression(pred[train_idx], actual[train_idx])
            model = fitted["model"]
            calibrated[test_idx] = self._predict_isotonic(
                pred[test_idx],
                model["x_thresholds"],
                model["y_thresholds"],
            )

        global_fit = self.apply_isotonic_regression(pred, actual)
        return {
            "calibrated_probabilities": np.clip(calibrated, 0.0, 1.0).tolist(),
            "global_model": global_fit["model"],
            "folds": folds,
        }

    def _predict_isotonic(
        self,
        probabilities: Sequence[float],
        x_thresholds: Sequence[float],
        y_thresholds: Sequence[float],
    ) -> np.ndarray:
        x = np.asarray(probabilities, dtype=float)
        if len(x_thresholds) == 0:
            return np.clip(x, 0.0, 1.0)
        xt = np.asarray(x_thresholds, dtype=float)
        yt = np.asarray(y_thresholds, dtype=float)
        pred = np.interp(x, xt, yt, left=yt[0], right=yt[-1])
        return np.clip(pred, 0.0, 1.0)
