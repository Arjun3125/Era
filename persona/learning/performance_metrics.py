# performance_metrics.py

import json
import os
from collections import defaultdict, Counter
from statistics import mean, stdev


class PerformanceMetrics:

    def __init__(self, storage_path="metrics_store"):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

        # Core decision records
        self.decisions = []  
        # {turn, domain, stance, confidence, outcome, regret, quality_score}

        # Coverage tracking
        self.coverage = defaultdict(int)

        # Success tracking
        self.success_count = defaultdict(int)
        self.failure_count = defaultdict(int)

        # Failure clustering
        self.failure_clusters = defaultdict(list)
        # key: (domain, situation_type, confidence_bucket)

        self._load()

    # ------------------------------------------------------------
    # DECISION RECORDING
    # ------------------------------------------------------------

    def record_decision(self, turn, domain, stance,
                        confidence, outcome,
                        regret_score=0.0,
                        situation_type="general"):

        quality = self.measure_decision_quality(
            confidence, outcome, regret_score
        )

        record = {
            "turn": turn,
            "domain": domain,
            "stance": stance,
            "confidence": confidence,
            "outcome": outcome,
            "regret": regret_score,
            "quality_score": quality,
            "situation_type": situation_type
        }

        self.decisions.append(record)

        # Coverage tracking
        self.coverage[domain] += 1

        # Success / failure tracking
        if outcome == "success":
            self.success_count[domain] += 1
        else:
            self.failure_count[domain] += 1
            bucket = self._confidence_bucket(confidence)
            cluster_key = (domain, situation_type, bucket)
            self.failure_clusters[cluster_key].append(turn)

        self._save()

    # ------------------------------------------------------------
    # QUALITY METRIC
    # ------------------------------------------------------------

    def measure_decision_quality(self, confidence, outcome, regret_score):
        """
        Quality = confidence * accuracy - regret
        accuracy = 1 for success, 0 for failure
        """

        accuracy = 1 if outcome == "success" else 0
        return (confidence * accuracy) - regret_score

    # ------------------------------------------------------------
    # SUCCESS RATE
    # ------------------------------------------------------------

    def success_rate(self, domain):
        total = self.success_count[domain] + self.failure_count[domain]
        if total == 0:
            return 0.0
        return self.success_count[domain] / total

    # ------------------------------------------------------------
    # WEAK DOMAIN DETECTION
    # ------------------------------------------------------------

    def detect_weak_domains(self, threshold=0.5):
        weak = []
        for domain in self.coverage:
            if self.success_rate(domain) < threshold:
                weak.append({
                    "domain": domain,
                    "success_rate": self.success_rate(domain),
                    "tested": self.coverage[domain]
                })
        return weak

    # ------------------------------------------------------------
    # STABILITY METRIC
    # ------------------------------------------------------------

    def measure_stability(self, window=100):
        """
        Stability = inverse variance of quality scores
        over last N turns.
        """

        if len(self.decisions) < window:
            return None

        recent = self.decisions[-window:]
        qualities = [d["quality_score"] for d in recent]

        if len(qualities) < 2:
            return None

        variability = stdev(qualities)
        stability_score = 1 / (1 + variability)

        return {
            "window": window,
            "variability": variability,
            "stability_score": stability_score
        }

    # ------------------------------------------------------------
    # IMPROVEMENT TRAJECTORY
    # ------------------------------------------------------------

    def show_improvement_trajectory(self, window=100):

        if len(self.decisions) < window * 2:
            return None

        early = self.decisions[:window]
        late = self.decisions[-window:]

        early_avg = mean([d["quality_score"] for d in early])
        late_avg = mean([d["quality_score"] for d in late])

        improvement = late_avg - early_avg

        return {
            "early_avg_quality": early_avg,
            "late_avg_quality": late_avg,
            "delta": improvement
        }

    # ------------------------------------------------------------
    # FAILURE CLUSTER SUMMARY
    # ------------------------------------------------------------

    def failure_cluster_summary(self):
        summary = []

        for key, turns in self.failure_clusters.items():
            domain, situation_type, confidence_bucket = key
            summary.append({
                "domain": domain,
                "situation_type": situation_type,
                "confidence_bucket": confidence_bucket,
                "num_failures": len(turns)
            })

        return summary

    # ------------------------------------------------------------
    # COVERAGE REPORT
    # ------------------------------------------------------------

    def coverage_report(self):
        return dict(self.coverage)

    # ------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------

    def _confidence_bucket(self, confidence):
        if confidence >= 0.75:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"

    def _save(self):
        with open(os.path.join(self.storage_path, "metrics.json"), "w") as f:
            json.dump({
                "decisions": self.decisions,
                "coverage": dict(self.coverage),
                "success_count": dict(self.success_count),
                "failure_count": dict(self.failure_count),
                "failure_clusters": {
                    str(k): v for k, v in self.failure_clusters.items()
                }
            }, f, indent=2)

    def _load(self):
        file_path = os.path.join(self.storage_path, "metrics.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)

            self.decisions = data.get("decisions", [])
            self.coverage.update(data.get("coverage", {}))
            self.success_count.update(data.get("success_count", {}))
            self.failure_count.update(data.get("failure_count", {}))
