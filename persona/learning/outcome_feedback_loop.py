# outcome_feedback_loop.py

from collections import defaultdict
from datetime import datetime


class OutcomeFeedbackLoop:

    def __init__(self, council, kis_engine):
        """
        council: CouncilAggregator (manages ministers)
        kis_engine: KnowledgeEngine (KIS)
        """
        self.council = council
        self.kis_engine = kis_engine
        self.outcome_history = []
        self.minister_failure_counts = defaultdict(int)
        self.doctrine_effectiveness = defaultdict(lambda: {"success": 0, "failure": 0})

    # -----------------------------------------------------
    # RECORD OUTCOME
    # -----------------------------------------------------

    def record_decision_outcome(self,
                                decision_id,
                                domain,
                                recommended_stance,
                                minister_votes,
                                knowledge_items_used,
                                doctrine_applied,
                                actual_outcome,
                                regret_score):

        record = {
            "decision_id": decision_id,
            "domain": domain,
            "stance": recommended_stance,
            "ministers": minister_votes,
            "knowledge_items": knowledge_items_used,
            "doctrine": doctrine_applied,
            "outcome": actual_outcome,
            "regret": regret_score,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.outcome_history.append(record)

        # 1️⃣ Minister Adjustment
        self._adjust_ministers(domain, minister_votes, actual_outcome)

        # 2️⃣ Knowledge Engine Reweight
        self.update_kis_weights(knowledge_items_used, actual_outcome)

        # 3️⃣ Doctrine Evaluation
        self._update_doctrine_effectiveness(doctrine_applied, actual_outcome)

    # -----------------------------------------------------
    # MINISTER RETRAINING
    # -----------------------------------------------------

    def _adjust_ministers(self, domain, minister_votes, outcome):

        for minister_name, stance in minister_votes.items():

            if outcome == "failure":
                self.minister_failure_counts[(minister_name, domain)] += 1
                self.council.adjust_confidence(minister_name, domain, -0.05)
            else:
                self.council.adjust_confidence(minister_name, domain, +0.02)

    def retrain_ministers(self, domain, failure_threshold=3):

        flagged = []

        for (minister_name, d), count in self.minister_failure_counts.items():
            if d == domain and count >= failure_threshold:

                self.council.adjust_confidence(minister_name, domain, -0.1)

                flagged.append({
                    "minister": minister_name,
                    "domain": domain,
                    "failures": count
                })

        return flagged

    # -----------------------------------------------------
    # KNOWLEDGE ENGINE REWEIGHTING
    # -----------------------------------------------------

    def update_kis_weights(self, knowledge_items_used, outcome):

        for item_id in knowledge_items_used:

            if outcome == "failure":
                self.kis_engine.adjust_weight(item_id, -0.05)
            else:
                self.kis_engine.adjust_weight(item_id, +0.02)

    # -----------------------------------------------------
    # DOCTRINE CHECKING
    # -----------------------------------------------------

    def _update_doctrine_effectiveness(self, doctrine_applied, outcome):

        if not doctrine_applied:
            return

        if outcome == "success":
            self.doctrine_effectiveness[doctrine_applied]["success"] += 1
        else:
            self.doctrine_effectiveness[doctrine_applied]["failure"] += 1

    def doctrine_report(self):

        report = {}

        for doctrine, stats in self.doctrine_effectiveness.items():

            total = stats["success"] + stats["failure"]
            if total == 0:
                continue

            success_rate = stats["success"] / total

            report[doctrine] = {
                "success_rate": success_rate,
                "total_uses": total
            }

        return report
