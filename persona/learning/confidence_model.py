# confidence_model.py

from collections import defaultdict


class BayesianConfidence:

    def __init__(self):
        # domain -> {alpha, beta}
        self.domains = defaultdict(lambda: {"alpha": 5, "beta": 2})
        # initial prior = 5 successes, 2 failures → 0.71 baseline confidence

    def update(self, domain, outcome):
        """
        outcome: "success" or "failure"
        """
        if outcome == "success":
            self.domains[domain]["alpha"] += 1
        elif outcome == "failure":
            self.domains[domain]["beta"] += 1

    def get_confidence(self, domain):
        data = self.domains[domain]
        alpha = data["alpha"]
        beta = data["beta"]
        return alpha / (alpha + beta)

    def get_uncertainty(self, domain):
        data = self.domains[domain]
        alpha = data["alpha"]
        beta = data["beta"]
        return 1 / (alpha + beta)

    def summary(self):
        return {
            d: self.get_confidence(d)
            for d in self.domains
        }
