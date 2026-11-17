"""
ears/extraction/entity_linker.py — Links ambient observations to known entities
in Era's Personal World Model (data/pwm/entities.json).
"""
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import List, Dict, Any, Optional

_entity_lock = threading.Lock()

from ears.config import ERA_ROOT

PWM_DIR = ERA_ROOT / "data" / "pwm"
ENTITIES_FILE = PWM_DIR / "entities.json"

# Common relationship keywords to look for in conversational observations
RELATIONSHIP_KEYWORDS = {
    "coworker": "work",
    "colleague": "work",
    "manager": "work",
    "boss": "work",
    "client": "work",
    "friend": "social",
    "roommate": "social",
    "mom": "family",
    "mother": "family",
    "dad": "family",
    "father": "family",
    "brother": "family",
    "sister": "family",
    "wife": "relationships",
    "husband": "relationships",
    "partner": "relationships",
}


def load_entities() -> Dict[str, Any]:
    """Load persistent entity profiles from disk."""
    with _entity_lock:
        PWM_DIR.mkdir(parents=True, exist_ok=True)
        if not ENTITIES_FILE.exists():
            default_data = {"entities": {}}
            try:
                with open(ENTITIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[entity_linker] warning: failed to initialize entities.json: {e}")
            return default_data
        try:
            with open(ENTITIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[entity_linker] warning: failed to read entities.json: {e}")
            return {"entities": {}}


def save_entities(data: Dict[str, Any]) -> None:
    """Save updated entity profiles to disk."""
    with _entity_lock:
        try:
            PWM_DIR.mkdir(parents=True, exist_ok=True)
            with open(ENTITIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[entity_linker] warning: failed to save entities.json: {e}")


def _extract_potential_names(text: str) -> List[str]:
    """Extract capitalized words that look like personal names."""
    if not text:
        return []
    # Match capitalized words not at the very start of a sentence or standard stopwords
    stopwords = {"The", "A", "An", "In", "On", "At", "To", "For", "Of", "With", "By", "From", "User", "Self", "Speaker", "Person", "Around", "None"}
    words = re.findall(r'\b[A-Z][a-z]{2,15}\b', text)
    return [w for w in set(words) if w not in stopwords]


def get_or_create_entity(entities_data: Dict[str, Any], name_or_rel: str, category: str = "social") -> Dict[str, Any]:
    """Retrieve an existing entity or create a new profile in the World Model."""
    entities = entities_data.setdefault("entities", {})
    key = name_or_rel.lower().replace(" ", "_")
    
    if key not in entities:
        entities[key] = {
            "entity_id": key,
            "name": name_or_rel.title(),
            "relationship": category,
            "interaction_count": 0,
            "historical_emotional_tones": [],
            "last_seen": None,
            "notes": f"Auto-enrolled via ambient sensory memory ({category})."
        }
    return entities[key]


def link_and_update_entities(facts: List[Dict[str, Any]], conversation_transcript: str) -> List[Dict[str, Any]]:
    """
    Inspect extracted facts and transcript for entity mentions.
    Update entity profiles with interaction counts and emotional tones,
    and attach linked_entities to each fact.
    """
    if not facts:
        return facts
        
    entities_data = load_entities()
    now = datetime.now(timezone.utc).isoformat()
    modified = False

    for fact in facts:
        content = fact.get("content", "")
        tone = fact.get("emotional_tone", "neutral")
        linked = []

        # 1. Check relationship keywords
        for kw, rel_category in RELATIONSHIP_KEYWORDS.items():
            if re.search(r'\b' + kw + r'\b', content, re.IGNORECASE) or re.search(r'\b' + kw + r'\b', conversation_transcript, re.IGNORECASE):
                entity = get_or_create_entity(entities_data, kw, rel_category)
                entity["interaction_count"] += 1
                entity["last_seen"] = now
                if tone and tone != "neutral":
                    entity["historical_emotional_tones"].append({"tone": tone, "timestamp": now})
                    entity["historical_emotional_tones"] = entity["historical_emotional_tones"][-10:] # Keep last 10
                if entity["name"] not in linked:
                    linked.append(entity["name"])
                modified = True

        # 2. Check personal names
        names = _extract_potential_names(content)
        for name in names:
            entity = get_or_create_entity(entities_data, name, "social")
            entity["interaction_count"] += 1
            entity["last_seen"] = now
            if tone and tone != "neutral":
                entity["historical_emotional_tones"].append({"tone": tone, "timestamp": now})
                entity["historical_emotional_tones"] = entity["historical_emotional_tones"][-10:]
            if entity["name"] not in linked:
                linked.append(entity["name"])
            modified = True

        fact["linked_entities"] = linked

    if modified:
        save_entities(entities_data)

    return facts
