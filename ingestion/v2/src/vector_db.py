"""Vector DB integration for ingestion pipeline — writes to Chroma."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_CHROMA_PATH = str(_PROJECT_ROOT / "chroma_knowledge")
_COLLECTION_NAME = "era_minister_knowledge"


class ChromaWriter:
    """Writes ingestion-produced knowledge into the runtime ChromaDB."""

    def __init__(
        self,
        chroma_path: str = _DEFAULT_CHROMA_PATH,
        collection_name: str = _COLLECTION_NAME,
    ) -> None:
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self._collection = None

    def _get_collection(self):
        """Get or create the Chroma collection."""
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.chroma_path)
            self._collection = client.get_or_create_collection(
                self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except Exception as e:
            print(f"[CHROMA] Failed to get collection: {e}")
            return None

    def index_minister_files(self, data_root: Optional[str] = None) -> int:
        """Read all minister JSON files and index into Chroma.

        Returns the number of documents added.
        """
        if data_root is None:
            data_root = str(_PROJECT_ROOT / "data" / "ministers")

        col = self._get_collection()
        if col is None:
            return 0

        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        ministers_path = Path(data_root)
        if not ministers_path.exists():
            print(f"[CHROMA] Ministers path does not exist: {data_root}")
            return 0

        for domain_dir in sorted(ministers_path.iterdir()):
            if not domain_dir.is_dir():
                continue
            domain = domain_dir.name

            for ktype in ("principles", "rules", "claims", "warnings"):
                json_file = domain_dir / f"{ktype}.json"
                if not json_file.exists():
                    continue

                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue

                # Handle both {"entries": [...]} and [...] formats
                if isinstance(data, dict):
                    entries = data.get("entries", [])
                elif isinstance(data, list):
                    entries = data
                else:
                    continue

                for entry in entries:
                    text = entry.get("text") or entry.get("content") or ""
                    if not text or not isinstance(text, str) or len(text.strip()) < 5:
                        continue

                    text_hash = f"{hash(text) & 0xFFFFFF:06x}"
                    entry_id = entry.get("id") or f"{domain}_{ktype}_{text_hash}"
                    doc_id = f"ingest_{domain}_{ktype}_{entry_id}"

                    documents.append(text)
                    metadatas.append({
                        "domain": domain,
                        "type": ktype.rstrip("s"),  # "principles" -> "principle"
                        "source": "ingestion",
                        "entry_id": str(entry_id),
                    })
                    ids.append(doc_id)

        # Batch add to Chroma (ChromaDB handles embedding internally)
        batch_size = 500
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            try:
                col.upsert(
                    documents=batch_docs,
                    metadatas=batch_meta,
                    ids=batch_ids,
                )
                total_added += len(batch_docs)
            except Exception as e:
                print(f"[CHROMA] Batch upsert failed at offset {i}: {e}")

        print(f"[CHROMA] Upserted {total_added} documents from minister files")
        return total_added

    def index_embeddings_json(self, embeddings_path: str) -> int:
        """Index pre-computed embeddings from 03_embeddings.json.

        Falls back to document-only mode if embeddings are zero-vectors.
        """
        col = self._get_collection()
        if col is None:
            return 0

        if not os.path.exists(embeddings_path):
            return 0

        try:
            with open(embeddings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return 0

        # Handle pipeline_metrics wrapper
        if isinstance(data, dict) and "pipeline_metrics" in data:
            data = data["pipeline_metrics"]
        if isinstance(data, dict) and "embeddings_created" in data:
            data = data["embeddings_created"]

        if not isinstance(data, list):
            return 0

        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for item in data:
            if not isinstance(item, dict):
                continue
            content = item.get("content", "")
            if not content:
                continue

            raw_id = item.get("id") or f"{hash(content) & 0xFFFFFF:06x}"
            doc_id = f"emb_{raw_id}"
            vec = item.get("embedding", [])

            # Skip zero-vectors (useless for similarity search)
            if not vec or (len(vec) == 1 and vec[0] == 0.0):
                documents.append(content)
                metadatas.append({
                    "domain": item.get("domain", "general"),
                    "type": item.get("field", "unknown"),
                    "source": "ingestion_embeddings",
                    "entry_id": item.get("id", ""),
                })
                ids.append(doc_id)
                continue

            documents.append(content)
            embeddings.append(vec)
            metadatas.append({
                "domain": item.get("domain", "general"),
                "type": item.get("field", "unknown"),
                "source": "ingestion_embeddings",
                "entry_id": item.get("id", ""),
            })
            ids.append(doc_id)

        if not documents:
            return 0

        batch_size = 500
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            try:
                kwargs: Dict[str, Any] = {
                    "documents": batch_docs,
                    "metadatas": batch_meta,
                    "ids": batch_ids,
                }
                if embeddings:
                    batch_embs = embeddings[i:i + batch_size]
                    if batch_embs:
                        kwargs["embeddings"] = batch_embs
                col.upsert(**kwargs)
                total_added += len(batch_docs)
            except Exception as e:
                print(f"[CHROMA] Embeddings batch upsert failed at offset {i}: {e}")

        print(f"[CHROMA] Upserted {total_added} embeddings from {embeddings_path}")
        return total_added


def write_ingestion_to_chroma(
    storage: str,
    data_root: Optional[str] = None,
    chroma_path: str = _DEFAULT_CHROMA_PATH,
) -> Dict[str, Any]:
    """Main entry point: after ingestion completes, sync to Chroma.

    Called from ingest_pipeline.py after Phase 3.5.
    """
    writer = ChromaWriter(chroma_path=chroma_path)

    # 1. Index minister JSON files (primary source of truth)
    minister_count = writer.index_minister_files(data_root=data_root)

    # 2. Index pre-computed embeddings if available (supplemental)
    embeddings_path = os.path.join(storage, "03_embeddings.json")
    embedding_count = 0
    if os.path.exists(embeddings_path):
        embedding_count = writer.index_embeddings_json(embeddings_path)

    return {
        "minister_docs_indexed": minister_count,
        "embedding_docs_indexed": embedding_count,
        "total_indexed": minister_count + embedding_count,
    }


# Legacy stubs for backward compatibility
from dataclasses import dataclass, field  # noqa: E402


@dataclass
class VectorIndexStub:
    data: List[Any] = field(default_factory=list)

    def add(self, record: Any) -> None:
        self.data.append(record)


class VectorDBStub:
    def __init__(self, storage_root: str = "data") -> None:
        self.combined_index = VectorIndexStub()
        self.base_index = VectorIndexStub()
        self.conflict_index = VectorIndexStub()
        self.strategy_index = VectorIndexStub()
        self.diplomacy_index = VectorIndexStub()
