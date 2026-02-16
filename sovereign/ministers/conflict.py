"""Minister of Conflict Module - Adversarial dynamics."""

from typing import Dict, Any
from . import MinisterModule


class ConflictModule(MinisterModule):
    """KIS-enhanced module for Conflict minister."""
    
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfConflict
        super().__init__("conflict", MinisterOfConflict, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["conflict_analysis"] = {
            "adversarial_indicators": ["vs", "against", "opposing", "competing", "threat"],
            "escalation_level": 0.5,
            "negotiation_feasibility": 0.7,
        }
        return kis


conflict_module = ConflictModule()

def get_conflict_module():
    return conflict_module
