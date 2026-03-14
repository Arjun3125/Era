"""Minister converter stubs for tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, Iterable, List


CATEGORIES = ("principles", "rules", "claims", "warnings")


def _category_payload(domain: str, category: str) -> Dict[str, object]:
    return {
        "domain": domain,
        "category": category,
        "entries": [],
        "meta": {"total_entries": 0},
    }


def ensure_minister_structure(domain_path: str) -> None:
    path = Path(domain_path)
    path.mkdir(parents=True, exist_ok=True)
    for category in CATEGORIES:
        file_path = path / f"{category}.json"
        if not file_path.exists():
            file_path.write_text(
                json.dumps(_category_payload(path.name, category), indent=2),
                encoding="utf-8",
            )
    doctrine_path = path / "doctrine.json"
    if not doctrine_path.exists():
        doctrine_path.write_text(
            json.dumps({"domain": path.name, "chapters": []}, indent=2),
            encoding="utf-8",
        )


def add_category_entry(domain_path: str, category: str, text: str, book_slug: str, chapter_index: int) -> str:
    ensure_minister_structure(domain_path)
    file_path = Path(domain_path) / f"{category}.json"
    data = json.loads(file_path.read_text(encoding="utf-8"))
    entry_id = uuid.uuid4().hex
    entry = {
        "id": entry_id,
        "text": text,
        "source": {"book": book_slug, "chapter": chapter_index},
        "weight": 1.0,
    }
    data["entries"].append(entry)
    data["meta"]["total_entries"] = len(data["entries"])
    file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return entry_id


def process_chapter_doctrine(chapter: Dict[str, object], book_slug: str, data_root: str) -> Dict[str, int]:
    domains = chapter.get("domains") or []
    results: Dict[str, int] = {}
    for domain in domains:
        domain_path = Path(data_root) / "ministers" / str(domain)
        ensure_minister_structure(str(domain_path))
        created = 0
        for category in CATEGORIES:
            for item in chapter.get(category, []) or []:
                add_category_entry(str(domain_path), category, str(item), book_slug, int(chapter.get("chapter_index", 0)))
                created += 1
        results[str(domain)] = created
    return results


def update_combined_vector_index(data_root: str) -> None:
    root = Path(data_root) / "ministers"
    combined = {
        "domain": "all",
        "combined": True,
        "domains_included": [],
        "domain_statistics": {},
    }
    if root.exists():
        for domain_dir in root.iterdir():
            if not domain_dir.is_dir():
                continue
            combined["domains_included"].append(domain_dir.name)
            total_entries = 0
            for category in CATEGORIES:
                file_path = domain_dir / f"{category}.json"
                if file_path.exists():
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    total_entries += len(data.get("entries", []))
            combined["domain_statistics"][domain_dir.name] = {
                "total_entries": total_entries,
            }
    combined_path = Path(data_root) / "combined_vector.index"
    combined_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")


def convert_all_doctrines(doctrines: List[Dict[str, object]], book_slug: str, data_root: str) -> Dict[str, object]:
    total_entries = 0
    domain_stats: Dict[str, Dict[str, int]] = {}
    for chapter in doctrines:
        results = process_chapter_doctrine(chapter, book_slug, data_root)
        for domain, created in results.items():
            total_entries += created
            stats = domain_stats.setdefault(domain, {"total_entries": 0})
            stats["total_entries"] += created
    update_combined_vector_index(data_root)
    return {
        "status": "success",
        "total_chapters_processed": len(doctrines),
        "total_entries_created": total_entries,
        "domain_statistics": domain_stats,
    }
