# performance_dashboard.py

class PerformanceDashboard:

    def __init__(self, metrics, mode_validator, identity_validator):
        self.metrics = metrics
        self.mode_validator = mode_validator
        self.identity_validator = identity_validator

    # -------------------------------------------------
    # ROLLING METRICS
    # -------------------------------------------------

    def compute_rolling_metrics(self, window=100):

        recent = self.metrics.decisions[-window:]

        if not recent:
            return {}

        success_rate = sum(
            1 for d in recent if d["outcome"] == "success"
        ) / len(recent)

        stability = self.metrics.measure_stability(window)

        return {
            "rolling_success_rate": success_rate,
            "stability": stability
        }

    # -------------------------------------------------
    # WEAK FEATURE ALERT
    # -------------------------------------------------

    def generate_weak_feature_alert(self):

        weak = self.metrics.detect_weak_domains(0.5)

        return weak

    # -------------------------------------------------
    # RETRAINING SUGGESTIONS
    # -------------------------------------------------

    def suggest_retraining_actions(self):

        suggestions = []

        weak = self.generate_weak_feature_alert()

        for domain_info in weak:
            suggestions.append(
                f"Increase retraining focus on {domain_info['domain']}"
            )

        if self.mode_validator.mode_stability_score() < 0.7:
            suggestions.append("Mode instability detected")

        return suggestions
