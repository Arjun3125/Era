"""Simple trace collector for Persona tests."""

from __future__ import annotations

import os
from typing import Any, Dict, List


TRACE: List[Dict[str, Any]] = []
DEBUG_OBSERVER = os.environ.get("PERSONA_DEBUG", "0") in {"1", "true", "yes", "on"}


def trace(event: str, data: Any | None = None) -> None:
    payload = {"event": str(event), "data": data}
    TRACE.append(payload)
    if DEBUG_OBSERVER:
        print(f"[TRACE] {payload}")
