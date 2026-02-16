"""
PersonaBrain (clean) — pure control layer

Minimal controller for deciding whether the assistant should `pass`, `halt`,
`suppress` or remain `silence`.

No I/O, no LLM calls, no state mutation.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ControlDirective:
    status: str
    action: str
    mode: Optional[str] = None
    reason: Optional[str] = None
    required_questions: Optional[List[str]] = None


class PersonaBrain:
    def decide(self, coherence: Dict[str, Any] | None, situation: Dict[str, Any], state: Dict[str, Any]) -> ControlDirective:
        s_type = (situation or {}).get("situation_type") or (situation or {}).get("type") or "unclear"
        try:
            clarity = float((situation or {}).get("clarity", 0.0) or 0.0)
        except (ValueError, TypeError) as _err:
            clarity = 0.0
            try:
                logger.warning("persona_brain_clean: invalid clarity %r, falling back to 0.0", (situation or {}).get("clarity"))
            except Exception:
                pass

        if s_type == "casual" and clarity < 0.3:
            return ControlDirective(status="silence", action="block", reason="low_clarity_casual")

        if clarity < 0.5:
            return ControlDirective(status="halt", action="ask", reason="clarify_needed", required_questions=["What outcome are you optimizing for?"])

        if coherence and isinstance(coherence, dict) and coherence.get("emotional_distortion"):
            return ControlDirective(status="suppress", action="ask", reason="emotional_distortion", required_questions=["What happens if you wait 24 hours?"])

        if s_type == "decision" and clarity >= 0.7:
            return ControlDirective(status="pass", action="speak", reason="clear_decision")

        return ControlDirective(status="halt", action="ask", reason="default_clarify", required_questions=["Can you say more about what outcome you want?"])