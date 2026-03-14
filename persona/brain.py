"""Minimal PersonaBrain decision logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ControlDirective:
    status: str
    action: str
    mode: str = "meeting"
    reason: str = ""
    questions: List[str] = field(default_factory=list)


class PersonaBrain:
    def decide(
        self,
        *,
        coherence: Dict[str, Any] | None = None,
        situation: Dict[str, Any] | None = None,
        state: Dict[str, Any] | None = None,
    ) -> ControlDirective:
        coherence = coherence or {}
        situation = situation or {}
        clarity = float(situation.get("clarity", 0.5))
        emotional = float(situation.get("emotional_load", 0.0))
        is_clear = bool(coherence.get("is_clear", clarity >= 0.4))

        if not is_clear and clarity <= 0.2:
            return ControlDirective(status="silence", action="block", reason="low_clarity")
        if not is_clear or clarity < 0.4:
            return ControlDirective(status="clarify", action="ask", reason="needs_context")
        if emotional >= 0.8:
            return ControlDirective(status="suppress", action="ground", reason="high_emotion")
        return ControlDirective(status="pass", action="speak", reason="clear_request")
