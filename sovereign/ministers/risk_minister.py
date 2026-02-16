"""
Risk minister implementation (simple, KIS-backed).
"""
from typing import Dict, Any, List
from persona.knowledge_engine import synthesize_knowledge
from .base_minister import BaseMinister


class RiskMinister(BaseMinister):
    def __init__(self, doctrine: Dict[str, Any] | None = None):
        super().__init__(name="risk_minister", domain="risk", doctrine=doctrine)

    def produce_advice(self, situation: Dict[str, Any], active_domains: List[str], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        # Use KIS to retrieve candidate knowledge
        try:
            extra_context = context.get("extra_context") if context else None
            kis_out = synthesize_knowledge(user_input=situation.get("text", ""), active_domains=active_domains, domain_confidence=situation.get("domain_confidence", 0.0), extra_context=extra_context)
            synthesized = kis_out.get("synthesized_knowledge", [])
            trace = kis_out.get("knowledge_trace", [])
            kq = kis_out.get("knowledge_quality", {})
            confidence = float(kq.get("candidate_quality", 0.0) or 0.0)
        except Exception:
            synthesized = []
            trace = []
            confidence = 0.0

        # Build supporting evidence list from backtrace
        supporting = []
        try:
            for item in trace[:3]:
                supporting.append({
                    "type": item.get("type") or "claim",
                    "book": item.get("book") or "builtin",
                    "kis": item.get("kis") or 0.0,
                })
        except Exception:
            supporting = []

        # Simple stance heuristic: if quality high -> support, moderate -> caution, low -> oppose
        if confidence >= 0.65:
            stance = "support"
        elif confidence >= 0.4:
            stance = "caution"
        else:
            stance = "oppose"

        primary_argument = synthesized[0] if synthesized else "No strong risk knowledge retrieved."

        # red line detection: simple doctrine check
        red_line = False
        try:
            red_keys = (self.doctrine or {}).get("red_lines", [])
            text = situation.get("text", "").lower()
            if red_keys and any(k.lower() in text for k in red_keys):
                red_line = True
        except Exception:
            red_line = False

        return {
            "minister": self.domain,
            "stance": stance,
            "confidence": round(confidence, 3),
            "primary_argument": primary_argument,
            "supporting_evidence": supporting,
            "second_order_effects": "Refer to supporting evidence for downstream risks.",
            "red_line_triggered": bool(red_line),
        }
