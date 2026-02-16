"""Minister of Truth Module - Reality enforcement."""
from typing import Dict, Any
from . import MinisterModule

class TruthModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfTruth
        super().__init__("truth", MinisterOfTruth, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["truth_factors"] = {
            "truth_keywords": ["true", "fact", "accurate", "verify", "honesty"],
            "accuracy_confidence": 0.85,
            "deception_risk": context.get("deception_likelihood", 0.2),
        }
        return kis

truth_module = TruthModule()
def get_truth_module():
    return truth_module
