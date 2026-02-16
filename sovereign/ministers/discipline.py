"""Minister of Discipline Module - Consistency and principles."""
from typing import Dict, Any
from . import MinisterModule

class DisciplineModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfDiscipline
        super().__init__("discipline", MinisterOfDiscipline, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["discipline_factors"] = {
            "consistency_keywords": ["consistent", "principle", "discipline", "adherence"],
            "contradiction_count": context.get("contradiction_count", 0),
            "principle_adherence": 0.8,
        }
        return kis

discipline_module = DisciplineModule()
def get_discipline_module():
    return discipline_module
