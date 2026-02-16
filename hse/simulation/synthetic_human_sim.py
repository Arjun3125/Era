# synthetic_human_sim.py

import random
from datetime import datetime


class SyntheticHumanSimulation:

    def __init__(self, human, llm_callable):
        """
        human: persistent SyntheticHuman object
        llm_callable(prompt) -> string
        """
        self.human = human
        self.llm = llm_callable
        self.human_history = []
        self.turn = 0

    # -------------------------------------------------
    # CORE LOOP
    # -------------------------------------------------

    def run_simulation_turn(self, persona_response):

        self.turn += 1

        # 1️⃣ Apply emotional reaction to Persona response
        self._update_internal_state(persona_response)

        # 2️⃣ Generate next human input via LLM
        next_input = self.generate_next_human_input(persona_response)

        # 3️⃣ Store conversation
        self.human_history.append({
            "turn": self.turn,
            "persona_response": persona_response,
            "human_response": next_input,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

        return next_input

    # -------------------------------------------------
    # HUMAN REACTION ENGINE
    # -------------------------------------------------

    def _update_internal_state(self, persona_response):

        # If persona response contains strong directive language,
        # human may feel controlled or resistant.

        if any(word in persona_response.lower() for word in ["must", "immediately", "cut", "stop"]):
            self.human.traits["impulsivity"] += 0.02
            self.human.traits["patience"] -= 0.01

        # If persona references past mistake → reduce impulsivity
        if "previous" in persona_response.lower() or "past failure" in persona_response.lower():
            self.human.traits["impulsivity"] -= 0.02
            self.human.traits["conscientiousness"] += 0.01

        # Escalate stress if crisis unresolved
        if self.human.unresolved:
            self.human.traits["patience"] -= 0.02

        # Clamp traits
        for t in self.human.traits:
            self.human.traits[t] = max(0.0, min(1.0, self.human.traits[t]))

    # -------------------------------------------------
    # GENERATE NEXT HUMAN INPUT
    # -------------------------------------------------

    def generate_next_human_input(self, persona_response):

        stress_level = 1 - self.human.traits["patience"]
        rebelliousness = self.human.traits["impulsivity"]
        risk_bias = self.human.traits["risk_tolerance"]

        unresolved = self.human.unresolved[-3:]

        prompt = f"""
You are a real human.

Profile:
Name: {self.human.name}
Traits: {self.human.traits}
Biases: {self.human.biases}
Unresolved issues: {unresolved}

Last advice from strategic Persona:
{persona_response}

Rules:
- You may follow, question, resist, or reinterpret the advice.
- If stress > 0.6, escalate emotionally.
- If impulsivity > 0.6, challenge authority.
- If risk_tolerance < 0.4, become cautious.
- Revisit unresolved issues naturally.
- Speak realistically.

Respond with your next move.
"""

        human_reply = self.llm(prompt)

        return human_reply.strip()

    # -------------------------------------------------
    # APPLY CONSEQUENCES TO HUMAN STATE
    # -------------------------------------------------

    def apply_consequences(self, decision_domain, outcome, severity=0.5):

        if outcome == "failure":

            self.human.unresolved.append(
                f"Failure in {decision_domain} domain"
            )

            # degrade trust
            self.human.traits["patience"] -= severity * 0.05
            self.human.traits["risk_tolerance"] -= severity * 0.05

        else:  # success

            # increase confidence
            self.human.traits["patience"] += 0.03
            self.human.traits["risk_tolerance"] += 0.02

        # Clamp values
        for t in self.human.traits:
            self.human.traits[t] = max(0.0, min(1.0, self.human.traits[t]))
