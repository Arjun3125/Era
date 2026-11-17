"""
ears/memory_bridge/episodic_writer.py — Appends ambient-derived episodes to
the same JSONL files your Persona N conversation loop already writes to
(Memory/YYYY-MM-DD_episodes.jsonl), using the same schema. Nothing in
episodic_memory.py, performance_metrics.py, or the 100-turn PWM sync needs
to change to pick these up — they just look like any other episode.
"""
import json
from datetime import date, datetime, timezone
import threading
from ears.config import MEMORY_DIR, ACTIVE_MEMORY_FILE
from ears.coaching.proactive_intervention import evaluate_and_trigger_coaching

_write_lock = threading.Lock()


def write_episode(episode: dict) -> None:
    # Ensure exact date and UTC timestamp is explicitly attached to the record
    episode.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    # 0. Evaluate for high-stress / anxiety proactive coaching interventions
    try:
        evaluate_and_trigger_coaching(episode)
    except Exception as e:
        print(f"[episodic_writer] warning: coaching evaluation failed: {e}")

    # 1. Write to daily file in Memory/ (as per README_EARS.md)
    with _write_lock:
        try:
            daily_filepath = MEMORY_DIR / f"{date.today().isoformat()}_episodes.jsonl"
            daily_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(daily_filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode) + "\n")

            # 2. Write to active project storage data/memory/episodes.jsonl (for EpisodicMemory integration)
            ACTIVE_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ACTIVE_MEMORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode) + "\n")
        except Exception as e:
            print(f"[episodic_writer] error writing episode: {e}")
