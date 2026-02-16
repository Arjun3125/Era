# consequence_engine.py

import random
from datetime import datetime


class ConsequenceEngine:

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.active_consequences = []  # pending future effects

    # -------------------------------------------------
    # REGISTER DECISION
    # -------------------------------------------------

    def register_decision(self, turn_id, domain, decision, confidence):
        """
        Generate probabilistic delayed consequences.
        """

        severity = self._estimate_severity(domain, decision, confidence)

        consequence = {
            "origin_turn": turn_id,
            "domain": domain,
            "decision": decision,
            "severity": severity,
            "remaining_turns": self.rng.randint(3, 10),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.active_consequences.append(consequence)

        return consequence

    # -------------------------------------------------
    # PROGRESS CONSEQUENCES
    # -------------------------------------------------

    def tick(self):
        """
        Progress consequences forward by one turn.
        Returns triggered events.
        """

        triggered = []

        for c in self.active_consequences:
            c["remaining_turns"] -= 1

            if c["remaining_turns"] <= 0:
                triggered.append(c)

        # remove triggered
        self.active_consequences = [
            c for c in self.active_consequences
            if c["remaining_turns"] > 0
        ]

        return triggered

    # -------------------------------------------------
    # SEVERITY ESTIMATION
    # -------------------------------------------------

    def _estimate_severity(self, domain, decision, confidence):

        base = 0.3

        if domain == "wealth":
            base = 0.6
        elif domain == "health":
            base = 0.7
        elif domain == "relationships":
            base = 0.5

        risk_factor = 1.0 - confidence

        randomness = self.rng.uniform(-0.1, 0.1)

        severity = max(0.1, min(1.0, base + risk_factor + randomness))

        return severity
