import random
from datetime import datetime

CRISIS_CATALOG = [
    {"id": "bankrupt", "label": "financial_crisis", "severity": 0.9, "domains": ["wealth","career"]},
    {"id": "breakup", "label": "relationship_breakup", "severity": 0.7, "domains": ["relationships","mental_state"]},
    {"id": "lawsuit", "label": "legal_trouble", "severity": 0.85, "domains": ["career","social_status"]},
    {"id": "diagnosis", "label": "health_diagnosis", "severity": 0.8, "domains": ["health","mental_state"]},
    {"id": "scandal", "label": "reputation_scandal", "severity": 0.75, "domains": ["social_status","career"]},
    {"id": "burnout", "label": "burnout", "severity": 0.6, "domains": ["health","learning","career"]}
]

class CrisisInjector:
    def __init__(self, seed=None, base_rate=0.05):
        self.rng = random.Random(seed)
        self.base_rate = base_rate  # probability per turn per human
        self.cooldowns = {}  # hid -> cooldown turns

    def maybe_inject(self, hid, human_profile, turn):
        cd = self.cooldowns.get(hid, 0)
        if cd > 0:
            self.cooldowns[hid] = cd - 1
            return None

        p = self.base_rate + min(0.2, human_profile.get("repetition", 0.0) * 0.1)
        if self.rng.random() < p:
            crisis = self.rng.choice(CRISIS_CATALOG)
            event = {
                "hid": hid,
                "crisis": crisis,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "turn": turn
            }
            # modify human_profile
            human_profile.setdefault("unresolved", []).append(crisis["label"])
            human_profile.setdefault("last_crisis_severity", 0.0)
            human_profile["last_crisis_severity"] = max(human_profile["last_crisis_severity"], crisis["severity"])
            self.cooldowns[hid] = 5 + int(crisis["severity"] * 10)
            return event
        return None
