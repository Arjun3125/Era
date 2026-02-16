"""Minister of Legitimacy Module - Values alignment."""
from typing import Dict, Any
from . import MinisterModule

class LegitimacyModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfLegitimacy
        super().__init__("legitimacy", MinisterOfLegitimacy, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["legitimacy_factors"] = {
            "authority_keywords": ["authority", "legal", "ethical", "values", "principle"],
            "ethical_alignment": 0.8,
            "authority_level": context.get("authority_score", 0.7),
        }
        return kis

legitimacy_module = LegitimacyModule()
def get_legitimacy_module():
    return legitimacy_module
