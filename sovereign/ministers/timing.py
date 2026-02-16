"""Minister of Timing Module - When to act."""
from typing import Dict, Any
from . import MinisterModule

class TimingModule(MinisterModule):
    def __init__(self, llm=None):
        from persona.ministers import MinisterOfTiming
        super().__init__("timing", MinisterOfTiming, llm)
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        kis = super().generate_kis(user_input, context)
        kis["timing_factors"] = {
            "urgency_keywords": ["now", "immediately", "urgent", "wait", "delay"],
            "urgency_level": context.get("urgency", 0.5),
            "readiness_score": 0.7,
        }
        return kis

timing_module = TimingModule()
def get_timing_module():
    return timing_module
