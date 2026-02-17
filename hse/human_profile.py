import random
from copy import deepcopy

class SyntheticHuman:
    def __init__(self, name=None, age=29, profession="Tech founder", seed=None):
        self.name = name or "Arjun"
        self.age = age
        self.profession = profession
        self.wealth = "Unstable startup income"
        # traits are represented as dict trait->0..1
        self.traits = {
            "ambitious": 0.8,
            "impatient": 0.6,
            "analytical": 0.7
        }
        self.unresolved_issues = []
        self.biases = []
        self.repetition = 0.0
        self.history = []
        self.seed = seed

    def profile(self):
        return {
            "name": self.name,
            "age": self.age,
            "profession": self.profession,
            "wealth": self.wealth,
            "traits": deepcopy(self.traits),
            "unresolved_issues": list(self.unresolved_issues),
            "biases": list(self.biases),
            "repetition": self.repetition,
        }

    def get(self, key, default=None):
        """Dict-like access for attributes."""
        return getattr(self, key, default)

    def __getitem__(self, key):
        """Dict-like getitem access."""
        return getattr(self, key)

    def __setitem__(self, key, value):
        """Dict-like setitem access."""
        setattr(self, key, value)

    def generate_context(self, domain: str) -> str:
        return f"""
Name: {self.name}
Age: {self.age}
Profession: {self.profession}
Wealth: {self.wealth}
Traits: {self.traits}
Current domain focus: {domain}
Unresolved issues: {self.unresolved_issues}
Speak as a real person experiencing real life.
"""

def build_user_prompt(human: SyntheticHuman, domain: str, coverage: dict) -> str:
    unused = [f for f, c in coverage.items() if c == 0]
    return f"""
You are a real human living your life.

Current life domain: {domain}

Profile:
{human.generate_context(domain)}

Act naturally.
Discuss real problems.
Return to past unresolved issues.
Test the Persona system.
Intentionally explore these unused features:
{unused}

Escalate complexity over time.
Behave like a psychologically real person.
"""
