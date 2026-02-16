"""Minister of Intelligence Module - Information quality."""
from typing import Dict, Any
from . import MinisterModule

class IntelligenceModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfIntelligence
        super().__init__("intelligence", MinisterOfIntelligence, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["intelligence_factors"] = {
            "awareness_keywords": ["unknown", "unclear", "hidden", "uncertain", "risk", "threat"],
            "information_gaps": context.get("known_unknowns", 0),
            "threat_assessment": 0.6,
        }
        return kis

intelligence_module = IntelligenceModule()
def get_intelligence_module():
    return intelligence_module
