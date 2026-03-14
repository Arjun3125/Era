"""Capital allocation stub for v2 ingestion."""
from __future__ import annotations

from typing import Any, Dict


def ingest_post_phase3(*_args, **_kwargs) -> Dict[str, Any]:
    """No-op placeholder for post-phase3 allocation."""
    return {"status": "skipped", "reason": "stub"}
