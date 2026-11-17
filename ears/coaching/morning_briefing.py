"""
ears/coaching/morning_briefing.py — Council of Ministers Morning Executive Briefing.

Synthesizes overnight memory digests, recent coaching alerts, and entity interactions
into a structured morning briefing from Era's Council of Ministers (Psychology/Discipline,
Grand Strategist/Career, and Risk/Health).
"""
import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from ears.config import ERA_ROOT
from ears.memory_bridge.sleep_cycle import load_consolidated_memories
from ears.extraction.entity_linker import load_entities
from persona.user_profile import get_or_create_profile, save_profile

BRIEFINGS_LOG_FILE = ERA_ROOT / "data" / "memory" / "morning_briefings.jsonl"
COACHING_LOG_FILE = ERA_ROOT / "data" / "memory" / "coaching_interventions.jsonl"

_briefing_lock = threading.Lock()


def load_recent_coaching_alerts(limit: int = 5) -> List[Dict[str, Any]]:
    """Load the most recent proactive coaching alerts."""
    if not COACHING_LOG_FILE.exists():
        return []
    alerts = []
    try:
        with open(COACHING_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    alerts.append(json.loads(line))
        return alerts[-limit:]
    except Exception:
        return []


def generate_morning_briefing() -> Dict[str, Any]:
    """
    Generate a multi-minister morning executive briefing based on the latest
    Overnight Sleep Cycle digest, recent entity interactions, and coaching alerts.
    """
    with _briefing_lock:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        date_str = now_iso[:10]

        # 1. Gather context
        consolidated_data = load_consolidated_memories()
        digests = consolidated_data.get("digests", [])
        latest_digest = digests[-1] if digests else {}

        entities_data = load_entities()
        entities = entities_data.get("entities", {})
        recent_alerts = load_recent_coaching_alerts()

        # Extract stats from latest digest
        total_ep = latest_digest.get("total_episodes_analyzed", 0)
        domains_dist = latest_digest.get("domains_distribution")
        if not isinstance(domains_dist, dict):
            domains_dist = {}
        tones_dist = latest_digest.get("emotional_tones_distribution")
        if not isinstance(tones_dist, dict):
            tones_dist = {}
        top_entities = latest_digest.get("top_entities_interacted")
        if not isinstance(top_entities, list):
            top_entities = []
        coaching_count = latest_digest.get("coaching_interventions_count", len(recent_alerts))

        dominant_domain = max(domains_dist.items(), key=lambda x: x[1])[0] if domains_dist else "general"
        dominant_tone = max(tones_dist.items(), key=lambda x: x[1])[0] if tones_dist else "neutral"

        # 2. Generate Minister Statements
        # Minister of Psychology & Discipline
        if dominant_tone in ["stressed", "anxious", "frustrated"]:
            psych_msg = (
                f"Your emotional baseline reflected elevated {dominant_tone} ({tones_dist.get(dominant_tone, 0)} observations). "
                "Maintain cognitive discipline today: compartmentalize friction and avoid reactive decision-making."
            )
        else:
            psych_msg = (
                f"Your emotional baseline is stable and {dominant_tone}. "
                "This is an optimal state for deep analytical focus and high-leverage execution."
            )

        # Minister of Grand Strategy & Career
        if top_entities:
            strat_msg = (
                f"Key interpersonal engagements included {', '.join(top_entities[:3])} across the {dominant_domain} domain. "
                "Ensure strategic alignment in upcoming communications and document action items promptly."
            )
        else:
            strat_msg = (
                f"Primary focus centered on {dominant_domain} activities. "
                "Prioritize long-term objective alignment over short-term reactive tasks today."
            )

        # Minister of Risk & Health
        if coaching_count > 0:
            risk_msg = (
                f"We logged {coaching_count} acute stress/anxiety triggers recently. "
                "Recommendation: Schedule a mandatory 15-minute screen-free decompression break before your afternoon meetings."
            )
        else:
            risk_msg = (
                "No critical cognitive load warnings detected. "
                "Maintain healthy sleep and nutritional habits to preserve cognitive endurance."
            )

        summary_text = f"[{date_str}] Morning Executive Briefing — Focus: {dominant_domain.upper()} | Baseline: {dominant_tone.upper()}."

        briefing_record = {
            "briefing_id": f"briefing_{date_str}",
            "timestamp": now_iso,
            "date": date_str,
            "context_analyzed": {
                "total_episodes": total_ep,
                "dominant_domain": dominant_domain,
                "dominant_tone": dominant_tone,
                "top_entities": top_entities,
                "coaching_alerts_count": coaching_count
            },
            "minister_statements": {
                "psychology_discipline": psych_msg,
                "grand_strategist": strat_msg,
                "risk_health": risk_msg
            },
            "summary": summary_text
        }

        # 3. Save to briefings log
        try:
            BRIEFINGS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BRIEFINGS_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(briefing_record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[morning_briefing] warning: failed to write briefing log: {e}")

        # 4. Update UserProfile notes
        try:
            profile = get_or_create_profile("default_user")
            note_entry = f"{summary_text}\n  - Psych: {psych_msg}\n  - Strat: {strat_msg}\n  - Risk: {risk_msg}"
            profile.notes = (note_entry + "\n\n" + profile.notes).strip()[:1500]
            save_profile(profile)
        except Exception as e:
            print(f"[morning_briefing] warning: failed to update UserProfile: {e}")

        print(f"\n[MORNING BRIEFING GENERATED] {summary_text}\n")
        return briefing_record
