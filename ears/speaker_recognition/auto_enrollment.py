"""
ears/speaker_recognition/auto_enrollment.py — Self-Supervised Acoustic Auto-Enrollment.

Analyzes conversational turn-taking patterns. When Self (Speaker 0) addresses someone
by name (e.g., "Hey Sarah", "Thanks Alex") and another speaker index replies immediately after,
it tracks correlation scores in data/pwm/voiceprint_candidates.json and auto-enrolls
when confidence reaches threshold (>= 75%).
"""
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ears.config import ERA_ROOT
from ears.speaker_recognition.voiceprint_engine import enroll_voiceprint, load_voiceprints

PWM_DIR = ERA_ROOT / "data" / "pwm"
CANDIDATES_FILE = PWM_DIR / "voiceprint_candidates.json"

_auto_lock = threading.Lock()

# Regex pattern to catch direct name address in speech
ADDRESS_PATTERN = re.compile(r'\b(?:Hey|Hi|Hello|Thanks|Ask|Listen|Tell|Okay|OK|No|Yes|Sorry|Wait|Look)\s+([A-Z][a-z]{2,15})\b')

# Words to ignore that look like capitalized names but aren't
IGNORE_NAMES = {"There", "User", "Self", "Speaker", "Person", "Around", "None", "Sir", "Maam", "God", "Man", "Dude", "Bro", "Today", "Tomorrow"}


def load_candidates() -> Dict[str, Any]:
    """Load persistent voiceprint candidate correlations from disk."""
    with _auto_lock:
        PWM_DIR.mkdir(parents=True, exist_ok=True)
        if not CANDIDATES_FILE.exists():
            default_data = {"candidates": {}}
            try:
                with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[auto_enrollment] warning: failed to initialize candidates: {e}")
            return default_data
        try:
            with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[auto_enrollment] warning: failed to read candidates: {e}")
            return {"candidates": {}}


def save_candidates(data: Dict[str, Any]) -> None:
    """Save updated voiceprint candidate correlations to disk."""
    with _auto_lock:
        try:
            PWM_DIR.mkdir(parents=True, exist_ok=True)
            with open(CANDIDATES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[auto_enrollment] warning: failed to save candidates: {e}")


def analyze_conversational_correlations(segments: List[Dict[str, Any]], auto_promote: bool = True) -> List[Dict[str, Any]]:
    """
    Inspect a sequence of diarized conversation segments.
    Look for turn pairs: [Speaker 0 says "Hey <Name>"] -> [Speaker X replies].
    Update candidate correlation counts and auto-enroll if confidence >= 0.75.
    """
    if not segments or len(segments) < 2:
        return []

    candidates_data = load_candidates()
    cands = candidates_data.setdefault("candidates", {})
    now = datetime.now(timezone.utc).isoformat()
    promoted_list: List[Dict[str, Any]] = []
    modified = False

    for i in range(len(segments) - 1):
        curr_seg = segments[i]
        next_seg = segments[i + 1]
        if not isinstance(curr_seg, dict) or not isinstance(next_seg, dict):
            continue

        curr_speaker = str(curr_seg.get("speaker", ""))
        next_speaker = str(next_seg.get("speaker", ""))

        # We want Self (0) addressing someone, followed by another speaker replying
        if curr_speaker == "0" and next_speaker != "0" and next_speaker not in ["", "None", "null"]:
            text = curr_seg.get("text", "")
            matches = ADDRESS_PATTERN.findall(text)
            
            for name in matches:
                if name in IGNORE_NAMES:
                    continue
                
                key = f"{next_speaker}_{name.lower()}"
                if key not in cands:
                    cands[key] = {
                        "candidate_id": key,
                        "speaker_label": next_speaker,
                        "candidate_name": name,
                        "correlation_count": 0,
                        "confidence": 0.0,
                        "first_detected": now,
                        "last_detected": now,
                        "status": "pending_correlation"
                    }
                
                record = cands[key]
                record["correlation_count"] += 1
                record["last_detected"] = now
                
                # Each correlation event adds 25% confidence
                record["confidence"] = min(1.0, record["correlation_count"] * 0.25)
                modified = True

                print(f"[AUTO-ENROLL CANDIDATE] Speaker {next_speaker} -> {name} (Confidence: {record['confidence']:.0%})")

                # Auto-promote if confidence threshold reached
                if auto_promote and record["confidence"] >= 0.75 and record["status"] != "promoted":
                    print(f"[AUTO-ENROLL PROMOTION] Promoting Speaker {next_speaker} to {name}!")
                    enroll_voiceprint(
                        speaker_label=next_speaker,
                        entity_name=name,
                        notes=f"Auto-enrolled via self-supervised acoustic correlation (count={record['correlation_count']})"
                    )
                    record["status"] = "promoted"
                    promoted_list.append(record)

    if modified:
        save_candidates(candidates_data)

    return promoted_list
