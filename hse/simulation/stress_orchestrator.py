# stress_orchestrator.py

class StressScenarioOrchestrator:

    def __init__(self, human, crisis_injector, arc):
        self.human = human
        self.crisis_injector = crisis_injector
        self.arc = arc
        self.active_scenario = None
        self.stress_log = []

    # -------------------------------------------------
    # RUN COMPOUNDING CRISIS
    # -------------------------------------------------

    def run_compounding_crisis(self, turn, crisis_chain):

        """
        crisis_chain = [
            {"turn_offset": 0, "domain": "career", "severity": 0.6},
            {"turn_offset": 20, "domain": "career", "severity": 0.9},
            {"turn_offset": 40, "domain": "health", "severity": 0.7},
            {"turn_offset": 60, "domain": "relationships", "severity": 0.8}
        ]
        """

        if self.active_scenario is None:
            self.active_scenario = {
                "start_turn": turn,
                "chain": crisis_chain,
                "completed": []
            }

        for stage in crisis_chain:
            target_turn = self.active_scenario["start_turn"] + stage["turn_offset"]

            if turn == target_turn:
                self._inject_stage(stage, turn)

    def _inject_stage(self, stage, turn):

        self.human.unresolved.append(
            f"{stage['domain']} crisis severity {stage['severity']}"
        )

        self.human.traits["patience"] -= stage["severity"] * 0.1
        self.human.traits["risk_tolerance"] -= stage["severity"] * 0.05

        self.arc.register_crisis(turn, stage["domain"], stage["severity"])

        self.stress_log.append({
            "turn": turn,
            "domain": stage["domain"],
            "severity": stage["severity"]
        })

    # -------------------------------------------------
    # MEASURE STRESS RESPONSE QUALITY
    # -------------------------------------------------

    def measure_stress_response_quality(self, metrics):

        stress_events = len(self.stress_log)
        failures_under_stress = 0

        for d in metrics.decisions:
            if any(c["domain"] == d["domain"] for c in self.stress_log):
                if d["outcome"] == "failure":
                    failures_under_stress += 1

        if stress_events == 0:
            return 1.0

        return 1 - (failures_under_stress / stress_events)
