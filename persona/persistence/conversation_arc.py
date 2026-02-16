# conversation_arc.py

from collections import defaultdict
from datetime import datetime


class ConversationArc:

    def __init__(self):

        self.original_problem = None
        self.original_domain = None

        self.decisions_made = []
        # [{turn, domain, decision, confidence}]

        self.consequences = []
        # [{origin_turn, current_turn, domain, magnitude}]

        self.crisis_history = []
        # [{turn_injected, domain, severity, resolved}]

        self.unresolved_issues = defaultdict(int)
        # domain -> recurrence count

        self.resolution_status = "open"
        # open | resolved | escalated

    # ---------------------------------------------------------
    # ORIGINAL PROBLEM TRACKING
    # ---------------------------------------------------------

    def set_original_problem(self, turn, domain, description):
        if self.original_problem is None:
            self.original_problem = {
                "turn": turn,
                "domain": domain,
                "description": description,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.original_domain = domain

    # ---------------------------------------------------------
    # DECISION CONTINUITY
    # ---------------------------------------------------------

    def record_decision(self, turn, domain, decision, confidence):
        self.decisions_made.append({
            "turn": turn,
            "domain": domain,
            "decision": decision,
            "confidence": confidence
        })

    def detect_decision_contradiction(self, domain, new_decision):
        contradictions = []

        for d in self.decisions_made:
            if d["domain"] == domain:
                if self._is_conflicting(d["decision"], new_decision):
                    contradictions.append(d)

        return contradictions

    # ---------------------------------------------------------
    # CONSEQUENCE TRACKING
    # ---------------------------------------------------------

    def track_decision_consequences(self,
                                    origin_turn,
                                    current_turn,
                                    domain,
                                    consequence_magnitude):

        self.consequences.append({
            "origin_turn": origin_turn,
            "current_turn": current_turn,
            "domain": domain,
            "magnitude": consequence_magnitude
        })

        if consequence_magnitude > 0.7:
            self.resolution_status = "escalated"

    def get_long_horizon_impact(self, min_turn_gap=50):

        long_effects = []

        for c in self.consequences:
            if c["current_turn"] - c["origin_turn"] >= min_turn_gap:
                long_effects.append(c)

        return long_effects

    # ---------------------------------------------------------
    # CRISIS NARRATIVE TRACKING
    # ---------------------------------------------------------

    def register_crisis(self, turn, domain, severity):
        self.crisis_history.append({
            "turn_injected": turn,
            "domain": domain,
            "severity": severity,
            "resolved": False
        })

    def resolve_crisis(self, domain):
        for crisis in reversed(self.crisis_history):
            if crisis["domain"] == domain and not crisis["resolved"]:
                crisis["resolved"] = True
                break

        if all(c["resolved"] for c in self.crisis_history):
            self.resolution_status = "resolved"

    # ---------------------------------------------------------
    # UNRESOLVED LOOP DETECTION
    # ---------------------------------------------------------

    def register_issue_reference(self, domain):
        self.unresolved_issues[domain] += 1

    def detect_unresolved_loop(self, threshold=3):

        loops = []

        for domain, count in self.unresolved_issues.items():
            if count >= threshold:
                loops.append({
                    "domain": domain,
                    "recurrence": count
                })

        return loops

    # ---------------------------------------------------------
    # INTERNAL
    # ---------------------------------------------------------

    def _is_conflicting(self, past_decision, new_decision):

        negative = ["reduce", "cut", "stop", "avoid"]
        positive = ["increase", "expand", "invest", "accelerate"]

        for neg in negative:
            for pos in positive:
                if neg in past_decision.lower() and pos in new_decision.lower():
                    return True
                if pos in past_decision.lower() and neg in new_decision.lower():
                    return True

        return False
