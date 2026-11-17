"""Capital allocation and post-ingestion analytics for v2 ingestion."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from .config import ALLOWED_DOMAINS

CATEGORIES = ["principles", "rules", "claims", "warnings"]


def ingest_post_phase3(event: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    """Compute post-ingestion capital allocation across minister domains."""
    if event is None:
        event = kwargs

    book_id = str(event.get("book_id", "unknown"))
    storage = str(event.get("storage", ""))
    mission_vector = event.get("mission_vector")

    search_dirs: List[str] = []
    if storage:
        search_dirs.append(os.path.join(storage, "ministers"))
    search_dirs.append(os.path.join("data", "ministers"))

    ministers_dir = None
    for d in search_dirs:
        if os.path.exists(d):
            ministers_dir = d
            break

    domain_distribution: Dict[str, Dict[str, Any]] = {}
    total_entries = 0

    if ministers_dir:
        for domain in ALLOWED_DOMAINS:
            domain_path = os.path.join(ministers_dir, domain)
            cat_counts: Dict[str, int] = {}
            dom_total = 0
            for cat in CATEGORIES:
                file_path = os.path.join(domain_path, f"{cat}.json")
                count = 0
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                count = len(data)
                    except Exception:
                        pass
                cat_counts[cat] = count
                dom_total += count

            domain_distribution[domain] = {
                "count": dom_total,
                "share": 0.0,
                "categories": cat_counts,
            }
            total_entries += dom_total

        if total_entries > 0:
            for domain in ALLOWED_DOMAINS:
                domain_distribution[domain]["share"] = (
                    domain_distribution[domain]["count"] / total_entries
                )

    report_path = None
    if storage:
        try:
            os.makedirs(storage, exist_ok=True)
            report_path = os.path.join(storage, "04_capital_allocation.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "book_id": book_id,
                        "total_entries": total_entries,
                        "domain_distribution": domain_distribution,
                        "mission_vector": mission_vector,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception:
            pass

    return {
        "status": "completed",
        "book_id": book_id,
        "total_entries": total_entries,
        "domain_distribution": domain_distribution,
        "report_path": report_path,
    }

