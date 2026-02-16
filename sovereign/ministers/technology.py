"""Minister of Technology Module - Technical feasibility."""
from typing import Dict, Any
from . import MinisterModule

class TechnologyModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfTechnology
        super().__init__("technology", MinisterOfTechnology, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["tech_factors"] = {
            "tech_keywords": ["system", "build", "code", "technical", "platform"],
            "technical_feasibility": 0.75,
            "resource_requirements": "medium",
        }
        return kis

technology_module = TechnologyModule()
def get_technology_module():
    return technology_module
