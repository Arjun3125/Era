"""Import CSDS knowledge into ERA's ChromaDB and minister files."""

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
COLLECTION_NAME = "era_minister_knowledge"

# Topic-to-domain mapping for ERA
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
    """Map CSDS topics to ERA domain."""
    if not topics_str:
        return "base"
    for topic, domain in TOPIC_DOMAIN_MAP.items():
        if topic.lower() in topics_str.lower():
            return domain
    return "base"


def import_to_chroma():
    """Import CSDS knowledge chunks into ERA's ChromaDB."""
    import chromadb

    print("[1/3] Connecting to CSDS database...")
    db = sqlite3.connect(CSDS_DB)
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM knowledge_chunks")
    total = cursor.fetchone()[0]
    print(f"  Found {total} knowledge chunks")

    print("[2/3] Connecting to ERA ChromaDB...")
    client = chromadb.PersistentClient(path=ERA_CHROMA)
    col = client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    existing = col.count()
    print(f"  Existing Chroma docs: {existing}")

    print("[3/3] Importing chunks...")
    batch_size = 500
    imported = 0
    skipped = 0

    cursor.execute("SELECT id, source, section, topics, text, embedding FROM knowledge_chunks")

    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break

        documents = []
        embeddings = []
        metadatas = []
        ids = []

        for row in rows:
            csds_id, source, section, topics, text, emb_str = row

            if not text or not emb_str:
                skipped += 1
                continue

            try:
                emb = json.loads(emb_str)
            except Exception:
                skipped += 1
                continue

            domain = get_domain_from_topics(topics or "")
            doc_id = f"csds_{csds_id}"

            documents.append(text)
            embeddings.append(emb)
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
                col.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                )
                imported += len(documents)
                if imported % 2000 == 0:
                    print(f"  Progress: {imported}/{total}")
            except Exception as e:
                print(f"  Batch upsert error: {e}")

    db.close()
    print(f"\nDone: {imported} imported, {skipped} skipped")
    print(f"Final Chroma count: {col.count()}")
    return imported


def import_contact_profiles():
    """Import CSDS contact profiles as ERA minister knowledge entries."""
    print("\n[Importing contact profiles...]")

    inbox_dir = Path("C:/Users/naren/Work/Projects/School/CSDS/data/inbox_json")
    summary_path = inbox_dir / "_summary.json"

    if not summary_path.exists():
        print("  No summary file found")
        return 0

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    conversations = summary.get("conversations", [])
    print(f"  Found {len(conversations)} conversations")

    # Create contacts domain directory
    contacts_dir = Path(ERA_MINISTERS) / "contacts"
    contacts_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for conv in conversations:
        name = conv.get("name", conv.get("conversation", "unknown"))
        total = conv.get("totalMessages", 0)
        narendra = conv.get("narendraMessageCount", 0)

        entry = {
            "id": f"contact_{hash(name) & 0xFFFFFF:06x}",
            "text": f"Contact: {name}. Total messages: {total}. Your messages: {narendra}. Relationship context from personal chat history.",
            "source": {"book": "csds:contacts", "chapter": 0},
            "weight": 1.0,
        }
        entries.append(entry)

    # Write as principles (relationship knowledge)
    output = {
        "domain": "contacts",
        "category": "principles",
        "entries": entries,
        "meta": {"source": "csds", "imported_at": int(time.time())},
    }

    with open(contacts_dir / "principles.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  Imported {len(entries)} contact profiles")
    return len(entries)


def import_personality_profile():
    """Import CSDS personality profile as ERA system config."""
    print("\n[Importing personality profile...]")

    config_path = Path("C:/Users/naren/Work/Projects/School/CSDS/config/personalityProfile.json")
    if not config_path.exists():
        print("  No personality profile found")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Save as ERA system config
    era_config_dir = Path(ERA_MINISTERS) / "_system"
    era_config_dir.mkdir(parents=True, exist_ok=True)

    with open(era_config_dir / "personality_profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"  Imported personality profile: {list(profile.keys())}")


def import_language_profile():
    """Import CSDS language profile for response style."""
    print("\n[Importing language profile...]")

    config_path = Path("C:/Users/naren/Work/Projects/School/CSDS/config/languageProfile.json")
    if not config_path.exists():
        print("  No language profile found")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    era_config_dir = Path(ERA_MINISTERS) / "_system"
    era_config_dir.mkdir(parents=True, exist_ok=True)

    with open(era_config_dir / "language_profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"  Imported language profile: {list(profile.keys())}")


if __name__ == "__main__":
    start = time.time()

    import_to_chroma()
    import_contact_profiles()
    import_personality_profile()
    import_language_profile()

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")
