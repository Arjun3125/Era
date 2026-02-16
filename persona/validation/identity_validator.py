# identity_validator.py

class IdentityValidator:

    def __init__(self, persona_doctrine):
        self.doctrine = persona_doctrine
        self.teachings = {}  # turn -> teaching

    # -------------------------------------------------
    # SELF CONTRADICTION
    # -------------------------------------------------

    def check_self_contradiction(self, turn_id, proposed_response):

        contradictions = []

        for past_turn, teaching in self.teachings.items():
            if "never" in teaching.lower():
                forbidden = teaching.split("never")[-1].strip()
                if forbidden and forbidden in proposed_response:
                    contradictions.append(past_turn)

        return contradictions

    # -------------------------------------------------
    # VOICE CONSISTENCY
    # -------------------------------------------------

    def validate_voice_consistency(self, response_history):

        if len(response_history) < 2:
            return 1.0

        recent = response_history[-10:]

        tone_words = ["strategic", "decisive", "sovereign"]

        score = 0

        for r in recent:
            if any(word in r.lower() for word in tone_words):
                score += 1

        return score / len(recent)

    # -------------------------------------------------
    # AUTHORITY BOUNDARY
    # -------------------------------------------------

    def enforce_authority_boundaries(self, response):

        if "you must marry" in response.lower():
            return False

        if "i will execute this for you" in response.lower():
            return False

        return True

    # -------------------------------------------------
    # PRIME CONFIDENT META-CHECK
    # -------------------------------------------------

    def meta_character_check(self, response):

        weak_markers = ["maybe", "perhaps", "i think", "i feel"]

        if any(w in response.lower() for w in weak_markers):
            return False

        return True
