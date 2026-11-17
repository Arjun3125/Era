# persona/learning/outcome_feedback.py
"""
Outcome Feedback Loop: Connects decisions to actual outcomes.
Updates minister confidence and KIS weights based on results.
"""

from typing import Dict, List, Any, Optional
from .episodic_memory import Episode

class OutcomeFeedbackLoop:
    def __init__(self, council=None, kis_engine=None, episodic_memory=None):
        self.council = council
        self.kis_engine = kis_engine
        self.episodic_memory = episodic_memory
        self.outcome_records: List[Dict[str, Any]] = []
    
    def record_decision_outcome(self, episode: Episode) -> bool:
        """
        Record what actually happened after a decision.
        Compare against what ministers recommended.
        """
        record = {
            "episode_id": episode.episode_id,
            "turn": episode.turn_id,
            "domain": episode.domain,
            "recommended_stance": episode.minister_stance,
            "actual_outcome": episode.outcome,
            "regret_score": episode.regret_score,
            "consequence_chain": episode.consequence_chain,
        }
        self.outcome_records.append(record)
        return True
    
    def retrain_ministers(self, domain: str, failure_cluster: List[Episode]):
        """
        If multiple failures in same domain, adjust minister calibration
        via the existing MinisterConfidenceTracker on the council.
        """
        if not self.council or not failure_cluster:
            return

        # Find the relevant minister
        minister_name = domain
        if minister_name not in self.council.ministers:
            return

        # Calculate success rate
        success_count = sum(1 for ep in failure_cluster if ep.outcome == "success")
        success_rate = success_count / len(failure_cluster) if failure_cluster else 0.0

        # If too many failures, penalize via Bayesian confidence tracker
        if success_rate < 0.5:
            tracker = getattr(self.council, '_confidence_tracker', None)
            if tracker is not None:
                for ep in failure_cluster:
                    is_success = ep.outcome == "success"
                    tracker.record_outcome(minister_name, domain, success=is_success)
                print(f"[RETRAIN] {minister_name} penalized via Bayesian tracker. Success rate: {success_rate:.2%}, episodes: {len(failure_cluster)}")
            else:
                print(f"[RETRAIN] {minister_name} has no confidence tracker; skipping. Success rate: {success_rate:.2%}")
    
    def update_kis_weights(self, knowledge_items_used: List[str], outcome: str):
        """
        If KIS items led to failure, penalize them for future use.
        """
        if not self.kis_engine or outcome != "failure":
            return
        
        # Mark items as having contributed to failure
        for item_id in knowledge_items_used:
            # kis_engine should have a mechanism to penalize entries
            if hasattr(self.kis_engine, 'penalize_entry'):
                self.kis_engine.penalize_entry(item_id)
    
    def check_and_retrain(self, failure_threshold: int = 2) -> Dict[str, Any]:
        """Scan episodic memory for failure clusters and retrain ministers above threshold."""
        if not self.episodic_memory:
            return {"retrained": []}

        all_clusters = self.episodic_memory.detect_failure_clusters()
        retrained = []
        for cluster_key, episodes in all_clusters.items():
            if len(episodes) >= failure_threshold:
                domain = episodes[0].domain if episodes else cluster_key.split("_")[0]
                self.retrain_ministers(domain, episodes)
                retrained.append({"cluster": cluster_key, "episodes": len(episodes), "domain": domain})

        return {"retrained": retrained}

    def detect_repeated_mistake(self, episode: Episode) -> Optional[Episode]:
        """
        Check if this decision is repeating a past mistake.
        """
        if not self.episodic_memory:
            return None
        
        past_mistake = self.episodic_memory.detect_pattern_repetition(
            episode.domain,
            episode.user_input
        )
        return past_mistake
