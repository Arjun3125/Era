"""Minister of Sovereign Module - Meta coherence."""
from typing import Dict, Any
from . import MinisterModule

class SovereignModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfSovereign
        super().__init__("sovereign", MinisterOfSovereign, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["sovereignty_factors"] = {
            "agency_keywords": ["I", "my", "decision", "I choose", "authority"],
            "self_determination": 0.85,
            "agency_clarity": context.get("agency_score", 0.8),
        }
        return kis

sovereign_module = SovereignModule()
def get_sovereign_module():
    return sovereign_module
