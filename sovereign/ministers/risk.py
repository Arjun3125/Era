"""Minister of Risk Module - Downside protection."""
from typing import Dict, Any
from . import MinisterModule

class RiskModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfRisk
        super().__init__("risk", MinisterOfRisk, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["risk_factors"] = {
            "risk_keywords": ["risk", "danger", "loss", "failure", "catastrophe"],
            "risk_level": context.get("risk_level", 0.5),
            "downside_scenarios": 2,
            "mitigation_available": True,
        }
        return kis

risk_module = RiskModule()
def get_risk_module():
    return risk_module
