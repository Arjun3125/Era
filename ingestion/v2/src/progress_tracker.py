"""Progress tracking and reporting utilities."""
import json
import os
import time
from typing import Optional, Dict, Any


def live_progress(
    storage: str,
    phase: str,
    message: str,
    *,
    current: Optional[int] = None,
    total: Optional[int] = None,
):
    """
    Write progress to both console and progress.json file.
    
    Args:
        storage: Storage directory path
        phase: Current phase identifier
        message: Progress message
        current: Current item count (optional)
        total: Total items count (optional)
    """
    payload = {
        "phase": phase,
        "message": message,
        "current": current,
        "total": total,
        "timestamp": time.time(),
    }

    # Console output (human-readable)
    if current is not None and total is not None:
        try:
            print(f"[{phase.upper()}] {message} ({current}/{total})", flush=True)
        except Exception:
            pass
    else:
        try:
            print(f"[{phase.upper()}] {message}", flush=True)
        except Exception:
            pass

    # progress.json (machine-readable) with legacy compatibility
    try:
        path = os.path.join(storage, "progress.json")
        os.makedirs(storage, exist_ok=True)

        legacy = {
            "current_phase": phase,
            "current_phase_name": message,
            "status": (
                "completed"
                if (current is not None and total is not None and current >= total)
                or phase == "completed"
                else "running"
            ),
            "percent": (
                int((current / total) * 100) if (current is not None and total) else (100 if phase == "completed" else 0)
            ),
            "counts": {"current": current, "total": total},
        }

        merged = {**payload, **legacy}

        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
    except Exception:
        pass


def update_progress(
    out_dir: str,
    *,
    phase: str,
    phase_name: str,
    status: str,
    percent: int = 0,
    counts: Optional[Dict[str, Any]] = None,
):
    """
    High-level progress update (wraps live_progress).
    
    Args:
        out_dir: Output directory
        phase: Phase identifier
        phase_name: Phase display name
        status: Status string
        percent: Completion percentage
        counts: Optional count dictionary
    """
    try:
        current = percent if percent is not None else None
        total = 100 if current is not None else None

        live_progress(
            out_dir,
            phase=phase,
            message=f"{phase_name} - {status}",
            current=current,
            total=total,
        )
    except Exception:
        pass