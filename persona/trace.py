# persona/trace.py
"""
Simple trace / observer utilities. Controlled via PERSONA_DEBUG environment var.
Traces are no-op by default to avoid noisy output; turn on for debugging.
"""

import os
from datetime import datetime

env_val = os.getenv("PERSONA_DEBUG", "").lower()
DEBUG_OBSERVER = env_val in {"1", "true", "yes", "on"}

# Optional file logging if PERSONA_TRACE_FILE is set (path)
TRACE_FILE = os.getenv("PERSONA_TRACE_FILE", "").strip()

TRACE = []


def _append_trace(event, data=None):
    TRACE.append({"ts": datetime.utcnow().isoformat() + "Z", "event": event, "data": data})


def trace(event, data=None):
    """
    Record an internal event. No-op unless DEBUG_OBSERVER is True.
    If TRACE_FILE is set we also append an immediate line to the file so you can inspect
    traces while the process is running.
    """
    if not DEBUG_OBSERVER:
        return
    try:
        _append_trace(event, data)
        if TRACE_FILE:
            try:
                with open(TRACE_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.utcnow().isoformat()}Z\t{event}\t{repr(data)}\n")
            except Exception:
                pass
    except Exception:
        # Never raise from trace to avoid breaking main flow
        pass


def print_trace():
    """
    Print and clear collected traces. Will only print if DEBUG_OBSERVER is True and there
    are entries.
    """
    if not DEBUG_OBSERVER or not TRACE:
        return

    print("\n--- OBSERVER TRACE ---")
    for item in TRACE:
        ts = item.get("ts")
        print(f"[{ts}] [{item['event']}] {item['data']}")
    print("--- END TRACE ---\n")
    TRACE.clear()