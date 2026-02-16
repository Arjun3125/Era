# human_persona_adapter.py

class HumanPersonaAdaptation:

    def __init__(self):
        self.adoption_history = []
        self.trust_score = 0.5  # 0 to 1

    # -------------------------------------------------
    # ADVICE ADOPTION
    # -------------------------------------------------

    def measure_advice_adoption(self, advice_given, subsequent_human_action):

        adoption = 0

        if any(word in subsequent_human_action.lower() for word in advice_given.lower().split()[:5]):
            adoption = 1
        elif "but" in subsequent_human_action.lower():
            adoption = 0.5
        else:
            adoption = 0

        self.adoption_history.append(adoption)

        return adoption

    # -------------------------------------------------
    # TRUST TRAJECTORY
    # -------------------------------------------------

    def measure_trust_trajectory(self, window=100):

        if not self.adoption_history:
            return self.trust_score

        recent = self.adoption_history[-window:]
        avg_adoption = sum(recent) / len(recent)

        self.trust_score = avg_adoption
        return self.trust_score

    # -------------------------------------------------
    # ADVERSARIAL PRESSURE
    # -------------------------------------------------

    def detect_challenge_behavior(self, human_input):

        adversarial_markers = ["why", "prove", "are you sure", "always", "never"]

        return any(m in human_input.lower() for m in adversarial_markers)
