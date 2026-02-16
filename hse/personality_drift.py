import random
from datetime import datetime

class PersonalityDrift:
    """
    Simple, debuggable personality drift engine.
    - small random walk on trait intensity
    - strong nudges on crisis or repeated success/failure signals
    """

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        # strengths scale how fast traits drift
        self.base_drift = 0.02

    def _mutate_trait(self, value, drift_scale):
        # value is in [0,1], small gaussian step, clipped
        step = self.rng.gauss(0, self.base_drift * drift_scale)
        v = max(0.0, min(1.0, value + step))
        return v

    def apply(self, human_profile, signals):
        """
        human_profile: dict-like with 'traits' mapping trait->0..1
        signals: dict; keys: 'stress', 'success_rate', 'repetition', 'ml_feedback' etc.
        Returns a dict {changed: {...}, timestamp, note}
        """
        stress = float(signals.get("stress", 0.0))  # 0..1
        success = float(signals.get("success_rate", 0.5))
        repetition = float(signals.get("repetition", 0.0))
        ml_feedback = float(signals.get("ml_feedback", 0.5))

        # compute drift scale: stress increases volatility
        drift_scale = 1.0 + stress * 3.0 - success * 1.5 + repetition * 1.0

        changed = {}
        for trait, val in dict(human_profile.get("traits", {})).items():
            new_val = self._mutate_trait(val, drift_scale)
            if abs(new_val - val) > 1e-4:
                changed[trait] = {"before": val, "after": new_val}
                human_profile["traits"][trait] = new_val

        # possibility of a new bias emerging after repeated failure
        if repetition > 0.6 and success < 0.4 and self.rng.random() < 0.25:
            bias = self._create_bias(human_profile)
            human_profile.setdefault("biases", []).append(bias)
            changed["new_bias"] = bias

        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "signals": signals,
            "changed": changed,
        }
        return record

    def _create_bias(self, human_profile):
        # cheap deterministic bias pick
        candidates = [
            "loss_aversion",
            "overfitting_to_recent_advice",
            "avoidance",
            "reckless_confidence",
            "confirmation_seeking"
        ]
        # prefer biases not already present
        present = set(human_profile.get("biases", []))
        remaining = [c for c in candidates if c not in present]
        if not remaining:
            remaining = candidates
        return self.rng.choice(remaining)
