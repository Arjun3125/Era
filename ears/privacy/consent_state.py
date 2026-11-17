"""
ears/privacy/consent_state.py — Tracks whether ambient capture is running in
SOLO mode (default: other speakers never stored) or ANNOUNCED_RECORDING
mode (you've told everyone present that this session is being recorded).

This is the single source of truth the rest of the pipeline checks before
persisting anything about a non-self speaker. It only changes via the
explicit calls below — wire these to a visible toggle/button in the phone
app, not to anything automatic.
"""
import json
import time
import threading
from ears.config import EARS_STATE_DIR, DEFAULT_MODE

_consent_lock = threading.Lock()

_STATE_FILE = EARS_STATE_DIR / "consent_state.json"

VALID_MODES = {"SOLO", "ANNOUNCED_RECORDING"}


def _load() -> dict:
    with _consent_lock:
        try:
            if _STATE_FILE.exists():
                return json.loads(_STATE_FILE.read_text())
        except Exception as e:
            print(f"[consent_state] warning: failed to read state file: {e}")
        return {"mode": DEFAULT_MODE, "changed_at": time.time(), "session_id": None}


def _save(state: dict) -> None:
    with _consent_lock:
        try:
            _STATE_FILE.write_text(json.dumps(state, indent=2))
        except Exception as e:
            print(f"[consent_state] warning: failed to save state file: {e}")


def get_mode() -> str:
    return _load()["mode"]


def start_announced_recording(session_id: str) -> dict:
    """Call this only after you've actually told the people present."""
    state = {"mode": "ANNOUNCED_RECORDING", "changed_at": time.time(), "session_id": session_id}
    _save(state)
    return state


def stop_announced_recording() -> dict:
    """Panic-button / end-of-meeting call. Always safe; reverts to SOLO."""
    state = {"mode": "SOLO", "changed_at": time.time(), "session_id": None}
    _save(state)
    return state


def is_third_party_storage_allowed() -> bool:
    return get_mode() == "ANNOUNCED_RECORDING"
