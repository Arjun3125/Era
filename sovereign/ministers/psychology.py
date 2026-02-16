"""Minister of Psychology Module - Human factors."""
from typing import Dict, Any
from . import MinisterModule

class PsychologyModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfPsychology
        super().__init__("psychology", MinisterOfPsychology, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["psychology_factors"] = {
            "emotion_keywords": ["feel", "emotion", "fear", "trust", "motivation"],
            "emotional_state": context.get("emotional_valence", 0.5),
            "psychological_safety": 0.7,
        }
        return kis

psychology_module = PsychologyModule()
def get_psychology_module():
    return psychology_module
