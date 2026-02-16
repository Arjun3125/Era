"""Minister of Adaptation Module - Change and system evolution."""

from typing import Dict, Any
from . import MinisterModule


class AdaptationModule(MinisterModule):
    """KIS-enhanced module for Adaptation minister."""
    
    def __init__(self, llm=None):
        # Import here to avoid circular dependency
        from persona.ministers import MinisterOfAdaptation
        super().__init__("adaptation", MinisterOfAdaptation, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate KIS data for adaptation domain."""
        kis = super().generate_kis(user_input, context)
        
        # Add adaptation-specific analysis
        kis["adaptation_signals"] = {
            "change_keywords": ["adapt", "evolve", "change", "transform", "evolve", "shift"],
            "persistence_score": context.get("turn_count", 0) / max(1, context.get("max_turns", 10)),
            "domain_variability": len(context.get("domains", [])) / 16.0  # 16 ministries
        }
        
        return kis


# Singleton instance
adaptation_module = AdaptationModule()


# Export
def get_adaptation_module():
    return adaptation_module
