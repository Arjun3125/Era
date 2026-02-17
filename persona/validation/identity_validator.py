# persona/validation/identity_validator.py
"""
Identity Validator: Ensures Persona remains coherent and doesn't contradict itself.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class IdentityValidator:
    def __init__(self, persona_doctrine: Dict[str, any] = None):
        self.doctrine = persona_doctrine
        self.teachings: Dict[int, str] = {}  # turn_id -> teaching given
        self.contradictions: List[Dict[str, any]] = []
    
    def record_teaching(self, turn_id: int, teaching: str):
        """Record something Persona taught."""
        self.teachings[turn_id] = teaching
    
    def check_self_contradiction(self, turn_id: int, proposed_response: str) -> Tuple[bool, Optional[str]]:
        """
        Check if proposed response contradicts past teachings.
        Returns (is_coherent, contradiction_description)
        """
        
        # Extract key claims from response
        key_claims = self._extract_claims(proposed_response)
        
        # Check against past teachings
        for past_turn, past_teaching in self.teachings.items():
            past_claims = self._extract_claims(past_teaching)
            
            # Simple contradiction detection
            contradiction = self._find_contradiction(key_claims, past_claims)
            if contradiction:
                return (False, f"Contradicts teaching from turn {past_turn}: {contradiction}")
        
        return (True, None)
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract key statements from text."""
        # Simple heuristic: sentences with "never", "always", "should", "must"
        claims = []
        for sentence in text.split("."):
            if any(word in sentence.lower() for word in ["never", "always", "should", "must", "cannot"]):
                claims.append(sentence.strip())
        return claims
    
    def _find_contradiction(self, new_claims: List[str], past_claims: List[str]) -> Optional[str]:
        """Find if any new claim contradicts past claim."""
        for new in new_claims:
            for past in past_claims:
                # Check for "never" vs "always" patterns
                if "never" in past.lower() and "always" in new.lower():
                    return f"Claimed 'never' but now saying 'always'"
                if "never" in new.lower() and "always" in past.lower():
                    return f"Claimed 'always' but now saying 'never'"
        return None
    
    def validate_voice_consistency(self, response_history: List[str]) -> float:
        """
        Measure if Persona sounds like itself.
        Returns consistency score 0.0-1.0.
        """
        if len(response_history) < 2:
            return 1.0
        
        # Simple metric: compare word patterns, sentence length, tone indicators
        # This is a placeholder; real implementation would use embeddings
        return 0.8  # Simplified for now
    
    def log_contradiction(self, turn_id: int, description: str, response: str, past_response: str):
        """Log a contradiction for review."""
        self.contradictions.append({
            "turn": turn_id,
            "description": description,
            "current_response": response,
            "past_response": past_response,
            "timestamp": datetime.utcnow().isoformat()
        })

