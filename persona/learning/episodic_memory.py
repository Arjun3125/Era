# persona/learning/episodic_memory.py
"""
Episodic Memory: Stores decisions, outcomes, and consequences for learning.
This is your PRIMARY LEARNING SYSTEM.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class Episode:
    """One decision + outcome + consequences."""
    episode_id: str
    turn_id: int
    domain: str  # e.g., "career_risk", "psychology"
    user_input: str
    persona_recommendation: str
    confidence: float
    minister_stance: str
    council_recommendation: str
    human_action: Optional[str] = None
    outcome: Optional[str] = None  # "success", "failure", "partial"
    regret_score: float = 0.0  # 0-1, how much human regretted
    consequence_chain: List[Tuple[int, str, str, float]] = None  # [(turn, domain, impact_type, magnitude)]
    lesson_learned: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.consequence_chain is None:
            self.consequence_chain = []


class EpisodicMemory:
    def __init__(self, storage_path: str = "data/memory/episodes.jsonl"):
        self.storage_path = storage_path
        self.episodes: Dict[str, Episode] = {}
        self.load_from_disk()
    
    def store_episode(self, episode: Episode) -> str:
        """Store a decision + outcome."""
        if not episode.episode_id:
            episode.episode_id = str(uuid.uuid4())[:8]
        self.episodes[episode.episode_id] = episode
        self._persist(episode)
        return episode.episode_id
    
    def _persist(self, episode: Episode):
        """Write to disk (append-only)."""
        try:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(episode)) + "\n")
        except Exception as e:
            print(f"[WARNING] Failed to persist episode: {e}")
    
    def load_from_disk(self):
        """Load all episodes from disk."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        ep = Episode(**data)
                        self.episodes[ep.episode_id] = ep
        except FileNotFoundError:
            pass
    
    def find_similar_episodes(self, domain: str, keyword: str = None) -> List[Episode]:
        """Retrieve past episodes in same domain."""
        matching = [
            ep for ep in self.episodes.values()
            if ep.domain == domain
        ]
        if keyword:
            matching = [
                ep for ep in matching
                if keyword.lower() in (ep.user_input or "").lower()
            ]
        return sorted(matching, key=lambda x: x.turn_id, reverse=True)
    
    def detect_pattern_repetition(self, current_domain: str, current_input: str) -> Optional[Episode]:
        """
        Check if repeating past mistake.
        Returns the similar past episode if found.
        """
        similar = self.find_similar_episodes(current_domain, current_input[:30])
        for ep in similar:
            if ep.outcome == "failure" and ep.regret_score >= 0.6:
                # This is a past mistake we're about to repeat
                return ep
        return None
    
    def detect_failure_clusters(self, domain: str = None) -> Dict[str, List[Episode]]:
        """Group failures by pattern."""
        failures = [
            ep for ep in self.episodes.values()
            if ep.outcome == "failure"
        ]
        if domain:
            failures = [ep for ep in failures if ep.domain == domain]
        
        clusters: Dict[str, List[Episode]] = {}
        for ep in failures:
            key = f"{ep.domain}_{ep.minister_stance}"
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(ep)
        return clusters
    
    def get_success_rate(self, domain: str = None) -> float:
        """Success rate for a domain or overall."""
        episodes = list(self.episodes.values())
        if domain:
            episodes = [ep for ep in episodes if ep.domain == domain]
        
        if not episodes:
            return 0.0
        
        successes = sum(1 for ep in episodes if ep.outcome == "success")
        return successes / len(episodes)
    
    def get_recent_episodes(self, num_turns: int = 100) -> List[Episode]:
        """Get last N turns."""
        sorted_eps = sorted(self.episodes.values(), key=lambda x: x.turn_id, reverse=True)
        return sorted_eps[:num_turns]
    
    def record_consequence(self, episode_id: str, turn: int, domain: str, impact_type: str, magnitude: float):
        """Track consequence as it unfolds."""
        if episode_id in self.episodes:
            ep = self.episodes[episode_id]
            ep.consequence_chain.append((turn, domain, impact_type, magnitude))
            self._persist(ep)
