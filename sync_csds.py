"""CSDS-to-ERA sync: imports new/updated knowledge from CSDS into ERA.

Run manually or set up as a scheduled task.
Tracks last sync timestamp to only import new data.
"""

import sqlite3
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

CSDS_DB = "C:/Users/naren/Work/Projects/School/CSDS/storage/csds.db"
ERA_CHROMA = "C:/Users/naren/Work/Projects/School/era/chroma_knowledge"
ERA_MINISTERS = "C:/Users/naren/Work/Projects/School/era/data/ministers"
SYNC_STATE = "C:/Users/naren/Work/Projects/School/era/data/memory/csds_sync_state.json"
COLLECTION_NAME = "era_minister_knowledge"

TOPIC_DOMAIN_MAP = {
    "Programming": "technology",
    "AI & LLM Tools": "technology",
    "Data Structures & Algorithms": "technology",
    "Devices & Hardware": "technology",
    "Creative & Media": "strategy",
    "Personal & Lifestyle": "psychology",
    "India & Local": "culture",
    "Entertainment & Culture": "culture",
    "Miscellaneous": "base",
    "Finance & Economics": "finance",
    "Health & Wellness": "discipline",
    "Education & Learning": "discipline",
    "Science": "truth",
    "Philosophy": "truth",
    "Psychology": "psychology",
    "Business": "strategy",
    "Sports": "discipline",
}


def get_domain_from_topics(topics_str: str) -> str:
    if not topics_str:
        return "base"
    for topic, domain in TOPIC_DOMAIN_MAP.items():
        if topic.lower() in topics_str.lower():
            return domain
    return "base"


def load_sync_state() -> dict:
    if os.path.exists(SYNC_STATE):
        with open(SYNC_STATE, "r") as f:
            return json.load(f)
    return {"last_sync_ts": 0, "last_chunk_count": 0, "sync_count": 0}


def save_sync_state(state: dict):
    os.makedirs(os.path.dirname(SYNC_STATE), exist_ok=True)
    with open(SYNC_STATE, "w") as f:
        json.dump(state, f, indent=2)


def sync_knowledge_chunks():
    """Sync new knowledge chunks from CSDS to ERA ChromaDB."""
    import chromadb

    state = load_sync_state()
    last_ts = state.get("last_sync_ts", 0)

    db = sqlite3.connect(CSDS_DB)
    cursor = db.cursor()

    # Get new/updated chunks since last sync
    cursor.execute(
        "SELECT id, source, section, topics, text, ts FROM knowledge_chunks WHERE ts > ? ORDER BY ts",
        (last_ts,),
    )
    new_rows = cursor.fetchall()

    if not new_rows:
        print("No new knowledge chunks since last sync")
        db.close()
        return 0

    print(f"Found {len(new_rows)} new/updated chunks")

    client = chromadb.PersistentClient(path=ERA_CHROMA)
    col = client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 500
    imported = 0

    for i in range(0, len(new_rows), batch_size):
        batch = new_rows[i : i + batch_size]
        documents = []
        metadatas = []
        ids = []

        for row in batch:
            csds_id, source, section, topics, text, ts = row
            if not text:
                continue

            domain = get_domain_from_topics(topics or "")
            doc_id = f"csds_{csds_id}"

            documents.append(text)
            metadatas.append({
                "domain": domain,
                "type": "knowledge",
                "source": f"csds:{source or 'unknown'}",
                "section": section or "",
                "topics": topics or "",
                "csds_id": csds_id,
            })
            ids.append(doc_id)

        if documents:
            try:
                col.upsert(documents=documents, metadatas=metadatas, ids=ids)
                imported += len(documents)
            except Exception as e:
                print(f"Batch upsert error: {e}")

    # Update sync state
    cursor.execute("SELECT MAX(ts) FROM knowledge_chunks")
    max_ts = cursor.fetchone()[0] or int(time.time())

    state["last_sync_ts"] = max_ts
    state["last_chunk_count"] = col.count()
    state["sync_count"] = state.get("sync_count", 0) + 1
    state["last_sync_time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save_sync_state(state)

    db.close()
    print(f"Imported {imported} chunks. Chroma total: {col.count()}")
    return imported


def sync_contact_profiles():
    """Sync contact profiles from CSDS inbox summary."""
    summary_path = Path("C:/Users/naren/Work/Projects/School/CSDS/data/inbox_json/_summary.json")
    if not summary_path.exists():
        return 0

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    conversations = summary.get("conversations", [])
    contacts_dir = Path(ERA_MINISTERS) / "contacts"
    contacts_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for conv in conversations:
        name = conv.get("name", conv.get("conversation", "unknown"))
        total = conv.get("totalMessages", 0)
        narendra = conv.get("narendraMessageCount", 0)

        entries.append({
            "id": f"contact_{hash(name) & 0xFFFFFF:06x}",
            "text": f"Contact: {name}. Total messages: {total}. Your messages: {narendra}. Relationship context from personal chat history.",
            "source": {"book": "csds:contacts", "chapter": 0},
            "weight": 1.0,
        })

    output = {
        "domain": "contacts",
        "category": "principles",
        "entries": entries,
        "meta": {"source": "csds", "imported_at": int(time.time())},
    }

    with open(contacts_dir / "principles.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Synced {len(entries)} contact profiles")
    return len(entries)


def sync_profiles():
    """Sync personality and language profiles."""
    era_config_dir = Path(ERA_MINISTERS) / "_system"
    era_config_dir.mkdir(parents=True, exist_ok=True)

    for name in ("personalityProfile.json", "languageProfile.json"):
        src = Path("C:/Users/naren/Work/Projects/School/CSDS/config") / name
        if src.exists():
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
            dst = era_config_dir / name.replace("Profile", "_profile").lower()
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Synced {name}")


if __name__ == "__main__":
    start = time.time()
    print("=== CSDS-to-ERA Sync ===")

    sync_knowledge_chunks()
    sync_contact_profiles()
    sync_profiles()

    elapsed = time.time() - start
    print(f"\nSync completed in {elapsed:.1f}s")
