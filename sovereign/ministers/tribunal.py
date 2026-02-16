"""Tribunal Module - Advisory judge (non-voting)."""
from typing import Dict, Any
from . import MinisterModule

class TribunalModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfTribunal
        super().__init__("tribunal", MinisterOfTribunal, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["tribunal_factors"] = {
            "accountability_keywords": ["accountable", "responsible", "consequences"],
            "accountability_level": context.get("accountability_score", 0.7),
            "consequence_clarity": 0.8,
        }
        return kis
    
    def invoke_with_prime(self, output, prime_confident_instance) -> Dict[str, Any]:
        """Tribunal provides advisory observation only (non-voting judge)."""
        result = super().invoke_with_prime(output, prime_confident_instance)
        result["advisory_note"] = "Tribunal is an observer, not a voting participant"
        return result

tribunal_module = TribunalModule()
def get_tribunal_module():
    return tribunal_module
