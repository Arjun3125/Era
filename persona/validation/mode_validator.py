# mode_validator.py

import re
from collections import defaultdict


class ModeValidator:

    def __init__(self):

        # Expected behavioral markers per mode
        self.mode_markers = {
            "quick": {
                "max_length": 120,
                "tone": ["direct"],
                "structure": False
            },
            "war": {
                "tone": ["must", "immediately", "cut", "stop", "decisive"],
                "avoid": ["understand", "feel", "empathy"],
                "structure": False
            },
            "meeting": {
                "structure": True,
                "markers": ["1.", "2.", "-", "agenda", "plan"],
                "tone": ["balanced"]
            },
            "darbar": {
                "structure": True,
                "markers": ["Minister", "Synthesis", "Perspective"],
                "tone": ["nuanced"]
            }
        }

        self.mode_history = []
        self.mode_switches = 0
        self.invalid_mode_count = defaultdict(int)

    # -----------------------------------------------------
    # VALIDATE MODE MATCH
    # -----------------------------------------------------

    def validate_response_mode_match(self, response, claimed_mode):

        score = 1.0
        issues = []

        mode = claimed_mode.lower()

        if mode not in self.mode_markers:
            return {"score": 0.0, "issues": ["Unknown mode"]}

        rules = self.mode_markers[mode]

        # 1️⃣ Length constraint for QUICK
        if mode == "quick":
            if len(response.split()) > rules["max_length"]:
                score -= 0.3
                issues.append("Too verbose for QUICK mode")

        # 2️⃣ WAR tone enforcement
        if mode == "war":
            if any(word in response.lower() for word in rules.get("avoid", [])):
                score -= 0.4
                issues.append("Empathetic tone detected in WAR mode")

            if not any(word in response.lower() for word in rules.get("tone", [])):
                score -= 0.2
                issues.append("Lacks decisive language")

        # 3️⃣ MEETING structure enforcement
        if mode == "meeting":
            if not any(marker in response for marker in rules.get("markers", [])):
                score -= 0.3
                issues.append("Missing structured format")

        # 4️⃣ DARBAR minister structure
        if mode == "darbar":
            if "minister" not in response.lower():
                score -= 0.5
                issues.append("Missing minister perspectives")

        return {
            "score": max(0.0, score),
            "issues": issues
        }

    # -----------------------------------------------------
    # MODE DRIFT DETECTION
    # -----------------------------------------------------

    def detect_mode_drift(self, current_mode, response):

        # Check if response contains strong markers of another mode
        drift_detected = False
        conflicting_mode = None

        for mode, rules in self.mode_markers.items():
            if mode == current_mode:
                continue

            markers = rules.get("markers", [])
            for marker in markers:
                if marker.lower() in response.lower():
                    drift_detected = True
                    conflicting_mode = mode
                    break

        return {
            "drift": drift_detected,
            "conflicting_mode": conflicting_mode
        }

    # -----------------------------------------------------
    # STABILITY TRACKING
    # -----------------------------------------------------

    def record_mode(self, mode):
        self.mode_history.append(mode)

        if len(self.mode_history) > 1:
            if self.mode_history[-1] != self.mode_history[-2]:
                self.mode_switches += 1

    def mode_stability_score(self, window=100):

        if len(self.mode_history) < 2:
            return 1.0

        recent = self.mode_history[-window:]
        switches = 0

        for i in range(1, len(recent)):
            if recent[i] != recent[i - 1]:
                switches += 1

        stability = 1 - (switches / len(recent))

        return max(0.0, stability)

    # -----------------------------------------------------
    # INCONSISTENCY SCORING
    # -----------------------------------------------------

    def inconsistency_score(self, validation_result):

        # Lower score means more inconsistent
        return 1 - validation_result["score"]
