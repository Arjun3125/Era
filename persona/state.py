from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any


@dataclass
class CognitiveState:
    mode: str = "quick"  # quick | war | meeting | darbar
    pending_mode_suggestion: Optional[str] = None
    mode_offer_made: bool = False
    pending_offer_text: Optional[str] = None
    last_emotional_load: float = 0.0
    last_visible_mode: Optional[str] = None
    mode_ttl: Optional[int] = None
    recent_turns: List[Tuple[str, str]] = field(default_factory=list)  # list of (user, assistant)
    turn_count: int = 0
    last_domain_classification_turn: int = -10
    domains: List[str] = field(default_factory=list)
    domain_confidence: float = 0.0
    domain_ttl: int = 0
    preferred_mode: Optional[str] = None
    forced_mode_bias: Optional[str] = None
    user_frequency: str = "medium"
    background_knowledge: Optional[dict] = None
    # New fields for latching & emotional metadata:
    domains_locked: bool = False  # when True, domains won't be replaced automatically
    emotional_metrics: Optional[dict] = None  # store last emotional metrics
    # any other runtime flags:
    last_domain_latched_at_turn: Optional[int] = None
    last_situation: Optional[dict] = None  # IMPROVEMENT: Track last situation for multi-turn context
    last_mode_eval: Optional[dict] = None  # IMPROVEMENT: Track mode fitness for better mode management
    
    # IMPROVEMENT: Methods for better state management
    def add_turn(self, user_prompt: str, assistant_response: str):
        """Add a turn to conversation history with automatic persistence."""
        self.recent_turns.append((user_prompt, assistant_response))
        # Keep only last 50 turns to prevent memory bloat
        if len(self.recent_turns) > 50:
            self.recent_turns = self.recent_turns[-50:]
        self.turn_count += 1
    
    def get_recent_context(self, num_turns: int = 5) -> List[Tuple[str, str]]:
        """Get the last N conversation turns for context building."""
        return self.recent_turns[-num_turns:] if self.recent_turns else []
    
    def update_domains(self, new_domains: List[str], confidence: float = 0.5):
        """Update domains with confidence tracking."""
        if new_domains and not self.domains_locked:
            self.domains = list(set(new_domains))  # Remove duplicates
            self.domain_confidence = max(confidence, 0.5 if new_domains else 0.0)
            return True
        return False
    
    def reset_for_new_conversation(self):
        """Reset state for a new conversation while preserving settings."""
        self.recent_turns.clear()
        self.turn_count = 0
        self.domains.clear()
        self.domain_confidence = 0.0
        self.domains_locked = False
        self.emotional_metrics = None
        self.background_knowledge = None