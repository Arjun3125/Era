"""
ears/speaker_recognition/voiceprint_engine.py — Manages acoustic profile enrollment
and resolves diarization speaker IDs (Speaker 1, Speaker 2) to enrolled entity names
in Era's Personal World Model.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import List, Dict, Any, Optional

_vp_lock = threading.Lock()

from ears.config import ERA_ROOT
from ears.extraction.entity_linker import load_entities, save_entities, get_or_create_entity

PWM_DIR = ERA_ROOT / "data" / "pwm"
VOICEPRINTS_FILE = PWM_DIR / "voiceprints.json"


def load_voiceprints() -> Dict[str, Any]:
    """Load persistent voiceprint registries from disk."""
    with _vp_lock:
        PWM_DIR.mkdir(parents=True, exist_ok=True)
        if not VOICEPRINTS_FILE.exists():
            default_data = {"voiceprints": {}}
            try:
                with open(VOICEPRINTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[voiceprint_engine] warning: failed to initialize voiceprints.json: {e}")
            return default_data
        try:
            with open(VOICEPRINTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[voiceprint_engine] warning: failed to read voiceprints.json: {e}")
            return {"voiceprints": {}}


def save_voiceprints(data: Dict[str, Any]) -> None:
    """Save updated voiceprint registries to disk."""
    with _vp_lock:
        try:
            PWM_DIR.mkdir(parents=True, exist_ok=True)
            with open(VOICEPRINTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[voiceprint_engine] warning: failed to save voiceprints.json: {e}")


def enroll_voiceprint(speaker_label: str, entity_name: str, relationship_category: str = "social", notes: str = "") -> Dict[str, Any]:
    """
    Enroll a speaker label (e.g., '1' or acoustic hash) to a specific entity name.
    Automatically ensures the entity profile exists in data/pwm/entities.json.
    """
    vp_data = load_voiceprints()
    entities_data = load_entities()
    
    # Ensure entity exists in PWM
    entity = get_or_create_entity(entities_data, entity_name, relationship_category)
    save_entities(entities_data)

    now = datetime.now(timezone.utc).isoformat()
    vp_id = f"vp_{speaker_label}"
    
    vp_record = {
        "voiceprint_id": vp_id,
        "entity_id": entity["entity_id"],
        "entity_name": entity["name"],
        "speaker_label": str(speaker_label),
        "enrolled_date": now,
        "notes": notes or f"Enrolled voiceprint for {entity['name']}."
    }
    
    vp_data.setdefault("voiceprints", {})[str(speaker_label)] = vp_record
    save_voiceprints(vp_data)
    print(f"[VOICEPRINT ENROLLED] Speaker {speaker_label} -> {entity['name']} ({entity['entity_id']})")
    return vp_record


def resolve_speaker_label(speaker_label: str) -> str:
    """
    Resolve a diarized speaker index (e.g., '1') to an enrolled entity name.
    Returns 'Person X (Around User)' if not enrolled.
    """
    if not speaker_label or str(speaker_label).strip() in ["", "None", "null"]:
        return "Unknown Person (Around User)"

    if str(speaker_label) == "0":
        return "Self (Speaker 0)"
        
    vp_data = load_voiceprints()
    vps = vp_data.get("voiceprints", {})
    
    if str(speaker_label) in vps:
        record = vps[str(speaker_label)]
        name = record.get("entity_name", f"Person {speaker_label}")
        return f"{name} (Enrolled Voice #{speaker_label})"
        
    return f"Person {speaker_label} (Around User)"
