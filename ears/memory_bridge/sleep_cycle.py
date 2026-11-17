"""
ears/memory_bridge/sleep_cycle.py — Overnight Memory Consolidation & Archiving Engine.

Runs during low-activity windows (e.g., 3:00 AM) to compress raw ambient episodes
into high-level statistical digests in Era's Personal World Model (consolidated_memories.json)
and archive raw transcripts older than 30 days to save high-speed vector retrieval space.
"""
import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

from ears.config import ERA_ROOT, ACTIVE_MEMORY_FILE

PWM_DIR = ERA_ROOT / "data" / "pwm"
CONSOLIDATED_FILE = PWM_DIR / "consolidated_memories.json"
ARCHIVE_DIR = ERA_ROOT / "data" / "memory" / "archive"

_sleep_lock = threading.Lock()


def load_consolidated_memories() -> Dict[str, Any]:
    """Load persistent consolidated memory digests from disk."""
    with _sleep_lock:
        PWM_DIR.mkdir(parents=True, exist_ok=True)
        if not CONSOLIDATED_FILE.exists():
            default_data = {"digests": []}
            try:
                with open(CONSOLIDATED_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[sleep_cycle] warning: failed to initialize consolidated_memories.json: {e}")
            return default_data
        try:
            with open(CONSOLIDATED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[sleep_cycle] warning: failed to read consolidated_memories.json: {e}")
            return {"digests": []}


def save_consolidated_memories(data: Dict[str, Any]) -> None:
    """Save updated consolidated memory digests to disk."""
    with _sleep_lock:
        try:
            PWM_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONSOLIDATED_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[sleep_cycle] warning: failed to save consolidated_memories.json: {e}")


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse ISO timestamp strings safely."""
    try:
        # Handle turn strings like 'ambient_2026-07-07T13:10:00+00:00'
        if ts_str.startswith("ambient_"):
            ts_str = ts_str.replace("ambient_", "")
        if ts_str.startswith("coach_"):
            ts_str = ts_str.replace("coach_", "")
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def run_sleep_cycle(archive_days: int = 30, force_archive: bool = False) -> Dict[str, Any]:
    """
    Execute overnight memory consolidation:
    1. Read active episodes from data/memory/episodes.jsonl.
    2. Compute domain frequencies, emotional tone distributions, and entity interactions.
    3. Generate and append a World Model digest to consolidated_memories.json.
    4. Archive episodes older than archive_days (or all if force_archive=True).
    """
    with _sleep_lock:
        if not ACTIVE_MEMORY_FILE.exists():
            return {"status": "skipped", "reason": "no active episodes file found"}

        episodes: List[Dict[str, Any]] = []
        try:
            with open(ACTIVE_MEMORY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        episodes.append(json.loads(line))
        except Exception as e:
            print(f"[sleep_cycle] error reading active memory: {e}")
            return {"status": "error", "reason": str(e)}

    if not episodes:
        return {"status": "skipped", "reason": "0 active episodes to consolidate"}

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    date_str = now_iso[:10]

    # 1. Statistical Aggregation
    domain_counter: Counter = Counter()
    tone_counter: Counter = Counter()
    entity_counter: Counter = Counter()
    coaching_count = 0

    retained_episodes: List[Dict[str, Any]] = []
    archived_episodes: List[Dict[str, Any]] = []

    cutoff_date = now - timedelta(days=archive_days)

    for ep in episodes:
        domain = ep.get("domain", "other")
        tone = ep.get("emotional_tone", "neutral")
        linked = ep.get("linked_entities", [])
        
        domain_counter[domain] += 1
        tone_counter[tone] += 1
        for ent in linked:
            entity_counter[ent] += 1
            
        if "coaching_intervention" in ep:
            coaching_count += 1

        # Check age for archiving
        ep_ts = _parse_timestamp(str(ep.get("turn", ""))) or _parse_timestamp(str(ep.get("timestamp", "")))
        if force_archive or (ep_ts and ep_ts < cutoff_date):
            archived_episodes.append(ep)
        else:
            retained_episodes.append(ep)

    dominant_domain = domain_counter.most_common(1)[0][0] if domain_counter else "none"
    dominant_tone = tone_counter.most_common(1)[0][0] if tone_counter else "neutral"
    top_entities = [ent for ent, _ in entity_counter.most_common(5)]

    summary_text = (
        f"Consolidated {len(episodes)} ambient observations. "
        f"Dominant domain: {dominant_domain} ({domain_counter[dominant_domain]}). "
        f"Dominant tone: {dominant_tone} ({tone_counter[dominant_tone]}). "
        f"Top linked entities: {', '.join(top_entities) if top_entities else 'None'}. "
        f"Proactive coaching interventions triggered: {coaching_count}."
    )

    digest = {
        "digest_id": f"digest_{date_str}_{len(episodes)}",
        "timestamp": now_iso,
        "total_episodes_analyzed": len(episodes),
        "domains_distribution": dict(domain_counter),
        "emotional_tones_distribution": dict(tone_counter),
        "top_entities_interacted": top_entities,
        "coaching_interventions_count": coaching_count,
        "summary_text": summary_text,
        "archived_count": len(archived_episodes)
    }

    # 2. Append Digest to PWM
    consolidated_data = load_consolidated_memories()
    consolidated_data.setdefault("digests", []).append(digest)
    save_consolidated_memories(consolidated_data)

    # 3. Archive older episodes if any
    if archived_episodes:
        with _sleep_lock:
            try:
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                archive_file = ARCHIVE_DIR / f"archive_{date_str}.jsonl"
                with open(archive_file, "a", encoding="utf-8") as af:
                    for a_ep in archived_episodes:
                        af.write(json.dumps(a_ep, ensure_ascii=False) + "\n")
                
                # Rewrite active memory with only retained episodes
                with open(ACTIVE_MEMORY_FILE, "w", encoding="utf-8") as f:
                    for r_ep in retained_episodes:
                        f.write(json.dumps(r_ep, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[sleep_cycle] warning during archiving: {e}")

    print(f"\n[SLEEP CYCLE COMPLETE] {summary_text}\n")
    return {
        "status": "success",
        "digest": digest,
        "retained_episodes": len(retained_episodes),
        "archived_episodes": len(archived_episodes)
    }
