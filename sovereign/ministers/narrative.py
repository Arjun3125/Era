"""Minister of Narrative Module - Story coherence."""
from typing import Dict, Any
from . import MinisterModule

class NarrativeModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfNarrative
        super().__init__("narrative", MinisterOfNarrative, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["narrative_factors"] = {
            "story_keywords": ["story", "narrative", "coherent", "arc", "theme"],
            "narrative_consistency": 0.8,
            "story_alignment": context.get("story_fit", 0.7),
        }
        return kis

narrative_module = NarrativeModule()
def get_narrative_module():
    return narrative_module
