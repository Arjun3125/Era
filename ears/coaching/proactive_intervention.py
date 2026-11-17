"""
ears/coaching/proactive_intervention.py — Evaluates ambient sensory observations
for critical emotional states (anxiety, stress, frustration) and triggers proactive
coaching recommendations and decompression strategies.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Dict, Any, Optional

_coach_lock = threading.Lock()

from ears.config import ERA_ROOT
from persona.user_profile import get_or_create_profile, save_profile

COACHING_LOG_FILE = ERA_ROOT / "data" / "memory" / "coaching_interventions.jsonl"

# Thresholds for triggering an automated intervention
CRITICAL_TONES = {"anxious", "stressed", "frustrated"}
CONFIDENCE_THRESHOLD = 0.75

DECOMPRESSION_STRATEGIES = {
    "anxious": "Detected acute anxiety/apprehension. Recommendation: Perform a 4-7-8 breathing cycle and review objective facts before your next meeting.",
    "stressed": "Detected elevated stress loading. Recommendation: Take a 10-minute screen-free decompression break or step outside to reset cognitive baseline.",
    "frustrated": "Detected interpersonal or operational frustration. Recommendation: Document specific friction points objectively before initiating conflict resolution."
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if isinstance(val, str):
            val = val.replace("%", "").strip()
            if float(val) > 1.0:
                return float(val) / 100.0
        return float(val)
    except (ValueError, TypeError):
        return default


def log_intervention(record: Dict[str, Any]) -> None:
    """Append a coaching intervention record to the persistent coaching log."""
    with _coach_lock:
        try:
            COACHING_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(COACHING_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[proactive_intervention] warning: failed to write coaching log: {e}")


def evaluate_and_trigger_coaching(episode: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluate an ambient episode. If emotional tone is critical and confidence is high,
    generate a coaching intervention, log it, and enrich the episode dictionary.
    """
    tone = episode.get("emotional_tone", "neutral")
    confidence = _safe_float(episode.get("confidence", 0.0))
    domain = episode.get("domain", "other")
    content = episode.get("content", "")

    if tone in CRITICAL_TONES and confidence >= CONFIDENCE_THRESHOLD:
        now = datetime.now(timezone.utc).isoformat()
        strategy = DECOMPRESSION_STRATEGIES.get(tone, "Take a brief decompression break.")
        
        intervention = {
            "intervention_id": f"coach_{now}",
            "timestamp": now,
            "trigger_turn": episode.get("turn", "unknown"),
            "domain": domain,
            "detected_tone": tone,
            "confidence": confidence,
            "trigger_content": content,
            "recommended_strategy": strategy,
            "status": "proactive_alert"
        }

        # 1. Log to dedicated interventions file
        log_intervention(intervention)

        # 2. Update UserProfile notes with latest alert
        with _coach_lock:
            try:
                profile = get_or_create_profile("default_user")
                alert_note = f"[{now[:10]}] Proactive Coaching ({tone.upper()}): {strategy}"
                profile.notes = (alert_note + "\n" + profile.notes).strip()[:1000] # Keep last 1000 chars
                save_profile(profile)
            except Exception as e:
                print(f"[proactive_intervention] warning: failed to update UserProfile: {e}")

        # 3. Attach to episode dictionary
        episode["coaching_intervention"] = strategy
        print(f"\n[PROACTIVE COACHING ALERT] Tone: {tone.upper()} ({confidence:.0%}) -> {strategy}\n")
        return intervention

    return None
