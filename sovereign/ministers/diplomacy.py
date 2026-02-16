"""Minister of Diplomacy Module - Stakeholder relationships."""
from typing import Dict, Any
from . import MinisterModule

class DiplomacyModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfDiplomacy
        super().__init__("diplomacy", MinisterOfDiplomacy, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["diplomacy_factors"] = {
            "stakeholder_keywords": ["partner", "stakeholder", "relationship", "trust", "ally"],
            "trust_level": context.get("trust_score", 0.5),
            "coalition_strength": len(context.get("domains", [])) / 16.0,
        }
        return kis

diplomacy_module = DiplomacyModule()
def get_diplomacy_module():
    return diplomacy_module
