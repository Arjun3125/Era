"""Minister of War Mode Module - Aggressive action."""
from typing import Dict, Any
from . import MinisterModule

class WarModeModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfWarMode
        super().__init__("war_mode", MinisterOfWarMode, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["war_factors"] = {
            "conflict_keywords": ["attack", "defend", "mobilize", "aggressive", "enemy"],
            "threat_level": context.get("threat_severity", 0.3),
            "mobilization_readiness": 0.8,
        }
        return kis

war_mode_module = WarModeModule()
def get_war_mode_module():
    return war_mode_module
