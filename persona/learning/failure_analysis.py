# failure_analysis.py

class FailureAnalysis:

    def __init__(self, council, kis_engine, mode_validator, arc, metrics):
        self.council = council
        self.kis_engine = kis_engine
        self.mode_validator = mode_validator
        self.arc = arc
        self.metrics = metrics

    # --------------------------------------------------
    # MAIN ANALYSIS ENTRY
    # --------------------------------------------------

    def analyze_failure(self,
                        decision_id,
                        domain,
                        persona_response,
                        minister_votes,
                        knowledge_items_used,
                        doctrine_applied,
                        emotional_distortion_detected,
                        claimed_mode):

        report = {
            "decision_id": decision_id,
            "domain": domain,
            "root_causes": [],
            "blame_assignment": {},
            "recommendations": []
        }

        # 1️⃣ Minister Analysis
        bad_ministers = self._analyze_minister_error(domain, minister_votes)
        if bad_ministers:
            report["root_causes"].append("Minister judgment error")
            report["blame_assignment"]["ministers"] = bad_ministers
            report["recommendations"].append("Reduce confidence weight of failing ministers")

        # 2️⃣ KIS Knowledge Check
        bad_kis = self._analyze_kis_error(knowledge_items_used)
        if bad_kis:
            report["root_causes"].append("Faulty knowledge selection")
            report["blame_assignment"]["kis"] = bad_kis
            report["recommendations"].append("Penalize knowledge weight")

        # 3️⃣ Mode Validation
        validation = self.mode_validator.validate_response_mode_match(
            persona_response,
            claimed_mode
        )

        if validation["score"] < 0.6:
            report["root_causes"].append("Mode mismatch")
            report["blame_assignment"]["mode"] = claimed_mode
            report["recommendations"].append("Tighten mode enforcement")

        # 4️⃣ Emotional Distortion
        if emotional_distortion_detected:
            report["root_causes"].append("Emotional distortion ignored")
            report["recommendations"].append("Increase emotional detection weight")

        # 5️⃣ Arc Loop Detection
        loops = self.arc.detect_unresolved_loop()
        if loops:
            report["root_causes"].append("Unresolved issue cycle")
            report["recommendations"].append("Escalate strategic reset")

        # 6️⃣ Consensus Flaw
        if self._consensus_was_flawed(minister_votes):
            report["root_causes"].append("Flawed council consensus")
            report["recommendations"].append("Rebalance minister influence weights")

        return report

    # --------------------------------------------------
    # SUB-CHECKS
    # --------------------------------------------------

    def _analyze_minister_error(self, domain, minister_votes):

        failing = []

        for minister_name, stance in minister_votes.items():
            confidence = self.council.get_confidence(minister_name, domain)
            if confidence < 0.4:
                failing.append(minister_name)

        return failing

    def _analyze_kis_error(self, knowledge_items):

        failing = []

        for item_id in knowledge_items:
            weight = self.kis_engine.get_weight(item_id)
            if weight < 0.4:
                failing.append(item_id)

        return failing

    def _consensus_was_flawed(self, minister_votes):

        unique_stances = set(minister_votes.values())
        return len(unique_stances) == 1  # unanimous but wrong = dangerous
