"""
Simple Council Aggregator that evaluates minister outputs and decides whether consensus exists.
"""
from typing import Dict, Any, List


class CouncilAggregator:
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = float(min_confidence)

    def evaluate(self, minister_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        # minister_outputs: domain -> output dict
        results = list(minister_outputs.values())
        if not results:
            return {"outcome": "irreconcilable_conflict", "reason": "no_ministers"}

        # If any red line triggered, escalate
        for m in results:
            if m.get("red_line_triggered"):
                return {"outcome": "irreconcilable_conflict", "reason": "red_line", "minister": m.get("minister")}

        # Count stances
        stance_counts = {"support": 0, "oppose": 0, "caution": 0}
        confidences: List[float] = []
        for m in results:
            s = m.get("stance") or "caution"
            if s in stance_counts:
                stance_counts[s] += 1
            try:
                confidences.append(float(m.get("confidence") or 0.0))
            except Exception:
                confidences.append(0.0)

        avg_conf = sum(confidences) / max(1, len(confidences))

        # Simple majority logic
        if stance_counts["support"] > max(stance_counts["oppose"], stance_counts["caution"]) and avg_conf >= self.min_confidence:
            return {"outcome": "consensus_reached", "recommendation": "support", "avg_confidence": avg_conf, "stance_counts": stance_counts}

        # Otherwise produce bounded tradeoff if mixed
        if stance_counts["oppose"] > 0 and stance_counts["support"] > 0:
            return {"outcome": "bounded_risk_tradeoff", "stance_counts": stance_counts, "avg_confidence": avg_conf}

        # fallback
        return {"outcome": "bounded_risk_tradeoff", "stance_counts": stance_counts, "avg_confidence": avg_conf}
