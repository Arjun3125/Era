import uuid
import json
import threading
from datetime import datetime
from copy import deepcopy

from personality_drift import PersonalityDrift

class SyntheticHuman:
    def __init__(self, name=None, seed=None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name or f"User_{self.id}"
        self.age = 28
        self.profession = "software"
        # traits in 0..1
        self.traits = {
            "curiosity": 0.7,
            "impulsivity": 0.3,
            "patience": 0.5,
            "risk_tolerance": 0.45,
            "openness": 0.6,
            "conscientiousness": 0.4
        }
        self.biases = []
        self.repetition = 0.0
        self.unresolved = []
        self.history = []
        self.seed = seed
        self.lock = threading.Lock()

    def profile(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "profession": self.profession,
            "traits": deepcopy(self.traits),
            "biases": list(self.biases),
            "repetition": self.repetition,
            "unresolved": list(self.unresolved)
        }

    def generate_context(self, domain: str) -> str:
        return f"""
Name: {self.name}
Age: {self.age}
Profession: {self.profession}
Traits: {self.traits}
Current domain focus: {domain}
Unresolved: {self.unresolved}
"""

    def snapshot(self):
        return {"timestamp": datetime.utcnow().isoformat() + "Z", "profile": self.profile()}

class PopulationManager:
    def __init__(self):
        self.humans = {}
        self.drift = PersonalityDrift()
        self.lock = threading.Lock()

    def create(self, n=1):
        created = []
        for _ in range(n):
            h = SyntheticHuman()
            self.humans[h.id] = h
            created.append(h)
        return created

    def list_ids(self):
        return list(self.humans.keys())

    def get(self, hid):
        return self.humans.get(hid)

    def save_state(self, path="population_state.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({hid: self.humans[hid].snapshot() for hid in self.humans}, f, indent=2)

    def apply_drift(self, hid, signals):
        h = self.get(hid)
        if not h: return None
        with h.lock:
            record = self.drift.apply(h.__dict__, signals)
            h.history.append({"drift": record})
            return record
