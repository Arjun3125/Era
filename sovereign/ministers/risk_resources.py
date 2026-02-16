"""Minister of Risk & Resources Module - Scarcity management."""
from typing import Dict, Any
from . import MinisterModule

class RiskResourcesModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfRiskResources
        super().__init__("risk_resources", MinisterOfRiskResources, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["resource_factors"] = {
            "resource_keywords": ["budget", "capital", "resources", "money", "reserves"],
            "resource_level": context.get("resource_availability", 0.6),
            "depletion_risk": 0.3,
        }
        return kis

risk_resources_module = RiskResourcesModule()
def get_risk_resources_module():
    return risk_resources_module
