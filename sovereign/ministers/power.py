"""Minister of Power Module - Capability and leverage."""
from typing import Dict, Any
from . import MinisterModule

class PowerModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfPower
        super().__init__("power", MinisterOfPower, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["power_factors"] = {
            "power_keywords": ["leverage", "pressure", "force", "strength", "advantage"],
            "power_asymmetry": context.get("power_imbalance", 0),
            "influence_radius": 0.6,
        }
        return kis

power_module = PowerModule()
def get_power_module():
    return power_module
