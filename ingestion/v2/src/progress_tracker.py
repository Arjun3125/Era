"""Progress tracking stub for v2 ingestion."""
from __future__ import annotations

from typing import Any, Dict


def live_progress(storage: str, **kwargs: Any) -> Dict[str, Any]:
    """No-op progress tracker; returns the payload for convenience."""
    return {"storage": storage, **kwargs}
