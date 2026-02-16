"""
memory.py
Simple MemoryReplay and Reconsolidation helpers.
"""
from typing import Any, Dict, List


class MemoryReplay:
    """Simulate replay and consolidation behavior.

    Methods:
      - consolidate(sequence) -> returns a "consolidated" representation
      - reconsolidate(existing, new_evidence) -> merged
    """

    def consolidate(self, sequence: List[Any]) -> Dict[str, Any]:
        # naive consolidation: return counts and snapshot
        try:
            return {
                "summary": str(sequence[:5]),
                "length": len(sequence),
            }
        except Exception:
            return {"summary": "", "length": 0}

    def reconsolidate(self, existing: Dict[str, Any], new_evidence: List[Any]) -> Dict[str, Any]:
        # merge summaries and update 'last_updated'
        out = dict(existing or {})
        out["recon_summary"] = str(new_evidence[:5])
        out["recon_count"] = (out.get("recon_count") or 0) + len(new_evidence)
        return out
