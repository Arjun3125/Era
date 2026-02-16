"""Minister of Optionality Module - Freedom preservation."""
from typing import Dict, Any
from . import MinisterModule

class OptionalityModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfOptionality
        super().__init__("optionality", MinisterOfOptionality, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["optionality_factors"] = {
            "option_keywords": ["option", "exit", "flexibility", "retreat", "alternative"],
            "option_count": context.get("available_options", 3),
            "reversibility": 0.7,
        }
        return kis

optionality_module = OptionalityModule()
def get_optionality_module():
    return optionality_module
