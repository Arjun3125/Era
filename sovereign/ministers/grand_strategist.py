"""Minister of Grand Strategy Module - Long-term vision."""
from typing import Dict, Any
from . import MinisterModule

class GrandStrategyModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfGrandStrategy
        super().__init__("grand_strategist", MinisterOfGrandStrategy, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["strategy_factors"] = {
            "longterm_keywords": ["future", "vision", "goal", "plan", "strategy", "legacy"],
            "time_horizon": context.get("time_horizon", 1),
            "strategic_alignment": 0.75,
        }
        return kis

grand_strategy_module = GrandStrategyModule()
def get_grand_strategy_module():
    return grand_strategy_module
