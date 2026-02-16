"""Phase 3.5: Minister Conversion - Converts extracted doctrine to domain-specific minister structure."""
import json
import os
import uuid
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path


def ensure_minister_structure(domain_path: str) -> None:
    """
    Create the complete directory structure for a minister domain.
    Creates consolidated JSON files for each category.
    
    Args:
        domain_path: Path to the domain minister folder (e.g., /data/ministers/constraints)
    """
    os.makedirs(domain_path, exist_ok=True)
    
    # Create consolidated JSON files for each category if they don't exist
    for category in ["principles", "rules", "claims", "warnings"]:
        category_file = os.path.join(domain_path, f"{category}.json")
        if not os.path.exists(category_file):
            initial_data = {
                "domain": os.path.basename(domain_path),
                "category": category,
                "entries": [],
                "meta": {
                    "total_entries": 0,
                    "last_updated": None,
                    "aggregated_from": []
                }
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    # Create doctrine.json as a summary file if it doesn't exist
    doctrine_file = os.path.join(domain_path, "doctrine.json")
    if not os.path.exists(doctrine_file):
        initial_doctrine = {
            "domain": os.path.basename(domain_path),
            "type": "domain_summary",
            "consolidated": True,
            "meta": {
                "total_entries": 0,
                "last_updated": None
            }
        }
        with open(doctrine_file, "w", encoding="utf-8") as f:
            json.dump(initial_doctrine, f, indent=2, ensure_ascii=False)


def add_category_entry(
    domain_path: str,
    category: str,
    text: str,
    book_slug: str,
    chapter_index: int,
    weight: float = 1.0
) -> str:
    """
    Add an entry to a consolidated category JSON file.
    
    Args:
        domain_path: Path to the domain minister folder
        category: One of ["principles", "rules", "claims", "warnings"]
        text: The entry text
        book_slug: Source book identifier
        chapter_index: Source chapter number
        weight: Importance weight (default 1.0)
        
    Returns:
        UUID of the created entry
    """
    entry_id = str(uuid.uuid4())
    category_file = os.path.join(domain_path, f"{category}.json")
    
    # Ensure the file exists
    if not os.path.exists(category_file):
        ensure_minister_structure(domain_path)
    
    # Load existing data
    with open(category_file, "r", encoding="utf-8") as f:
        category_data = json.load(f)
    
    # Add new entry
    entry = {
        "id": entry_id,
        "text": text,
        "source": {
            "book": book_slug,
            "chapter": chapter_index
        },
        "weight": weight
    }
    category_data["entries"].append(entry)
    
    # Track source
    source_key = {"book": book_slug, "chapter": chapter_index}
    if source_key not in category_data["meta"]["aggregated_from"]:
        category_data["meta"]["aggregated_from"].append(source_key)
    
    # Update metadata
    category_data["meta"]["total_entries"] = len(category_data["entries"])
    category_data["meta"]["last_updated"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    
    # IMPROVEMENT: Atomic write with temp file + rename (prevents JSON corruption)
    import tempfile
    temp_dir = os.path.dirname(category_file) or "."
    with tempfile.NamedTemporaryFile(mode="w", dir=temp_dir, delete=False, encoding="utf-8", suffix=".tmp") as tmp:
        json.dump(category_data, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        os.replace(tmp_path, category_file)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    
    return entry_id


def process_chapter_doctrine(
    chapter_data: Dict[str, Any],
    book_slug: str,
    data_root: str = "data",
    progress_cb: Optional[Callable] = None
) -> Dict[str, List[str]]:
    """
    Convert a single chapter's doctrine into minister domain structure.
    Adds entries to consolidated category JSON files.
    
    Args:
        chapter_data: Chapter doctrine object from phase 2
        book_slug: Identifier for the source book
        data_root: Root directory for data storage (default "data")
        progress_cb: Optional progress callback
        
    Returns:
        Dictionary mapping domain names to lists of created entry IDs
    """
    ministers_root = os.path.join(data_root, "ministers")
    domain_entries = {}
    
    domains = chapter_data.get("domains", [])
    chapter_index = chapter_data.get("chapter_index", 0)
    
    if progress_cb:
        progress_cb(
            phase="phase_3.5",
            message=f"Processing chapter {chapter_index} into {len(domains)} domains",
            current=0,
            total=len(domains)
        )
    
    for domain_idx, domain in enumerate(domains):
        domain_path = os.path.join(ministers_root, domain)
        domain_entries[domain] = []
        
        ensure_minister_structure(domain_path)
        
        # Process principles
        for principle in chapter_data.get("principles", []):
            principle_text = principle if isinstance(principle, str) else principle.get("statement", str(principle))
            entry_id = add_category_entry(
                domain_path, "principles", principle_text,
                book_slug, chapter_index
            )
            domain_entries[domain].append(entry_id)
        
        # Process rules
        for rule in chapter_data.get("rules", []):
            rule_text = rule if isinstance(rule, str) else str(rule)
            entry_id = add_category_entry(
                domain_path, "rules", rule_text,
                book_slug, chapter_index
            )
            domain_entries[domain].append(entry_id)
        
        # Process claims
        for claim in chapter_data.get("claims", []):
            claim_text = claim if isinstance(claim, str) else str(claim)
            entry_id = add_category_entry(
                domain_path, "claims", claim_text,
                book_slug, chapter_index
            )
            domain_entries[domain].append(entry_id)
        
        # Process warnings
        for warning in chapter_data.get("warnings", []):
            warning_text = warning if isinstance(warning, str) else str(warning)
            entry_id = add_category_entry(
                domain_path, "warnings", warning_text,
                book_slug, chapter_index
            )
            domain_entries[domain].append(entry_id)
        
        if progress_cb:
            progress_cb(
                phase="phase_3.5",
                message=f"Processed domain: {domain}",
                current=domain_idx + 1,
                total=len(domains)
            )
    
    return domain_entries


def convert_all_doctrines(
    doctrines: List[Dict[str, Any]],
    book_slug: str,
    data_root: str = "data",
    progress_cb: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Convert all doctrines from a book into minister structure.
    
    Args:
        doctrines: List of chapter doctrine objects
        book_slug: Identifier for the source book
        data_root: Root directory for data storage
        progress_cb: Optional progress callback
        
    Returns:
        Summary dict with conversion statistics
    """
    total_chapters = len(doctrines)
    total_entries = 0
    domain_stats = {}
    
    if progress_cb:
        progress_cb(
            phase="phase_3.5",
            message=f"Starting minister conversion for {total_chapters} chapters",
            current=0,
            total=total_chapters
        )
    
    # Parallel minister conversion (8 workers for I/O-bound file operations) - 4-8x speedup
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial
    
    process_fn = partial(process_chapter_doctrine, book_slug=book_slug, data_root=data_root)
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(
            process_fn,
            doctrines,
            timeout=60
        ))
        
        # Aggregate results and track progress
        for chapter_idx, chapter_domain_entries in enumerate(results):
            for domain, entries in chapter_domain_entries.items():
                if domain not in domain_stats:
                    domain_stats[domain] = 0
                domain_stats[domain] += len(entries)
                total_entries += len(entries)
            
            if progress_cb and chapter_idx % max(1, total_chapters // 10) == 0:  # Update every 10% or at least once per chapter
                progress_cb(
                    phase="phase_3.5",
                    message=f"Converted chapter {chapter_idx + 1}/{total_chapters} (parallel 8x)",
                    current=chapter_idx + 1,
                    total=total_chapters
                )
    
    if progress_cb:
        progress_cb(
            phase="phase_3.5",
            message=f"Converted chapter {total_chapters}/{total_chapters}",
            current=total_chapters,
            total=total_chapters
        )
    
    summary = {
        "status": "success",
        "total_chapters_processed": total_chapters,
        "total_entries_created": total_entries,
        "domains_populated": len(domain_stats),
        "domain_statistics": domain_stats
    }
    
    return summary


def update_combined_vector_index(
    data_root: str = "data"
) -> None:
    """
    Update the combined vector index metadata with current domain statistics.
    
    Args:
        data_root: Root directory for data storage
    """
    combined_index_path = os.path.join(data_root, "combined_vector.index")
    ministers_root = os.path.join(data_root, "ministers")
    
    domains = []
    domain_stats = {}
    
    # Scan all domains and count entries from consolidated category files
    if os.path.exists(ministers_root):
        for domain_name in os.listdir(ministers_root):
            domain_path = os.path.join(ministers_root, domain_name)
            if os.path.isdir(domain_path):
                entry_count = 0
                last_updated = None
                
                # Count entries across all category files
                for category in ["principles", "rules", "claims", "warnings"]:
                    category_file = os.path.join(domain_path, f"{category}.json")
                    
                    if os.path.exists(category_file):
                        with open(category_file, "r", encoding="utf-8") as f:
                            category_data = json.load(f)
                        
                        entries = category_data.get("entries", [])
                        entry_count += len(entries)
                        
                        # Track last updated
                        updated = category_data.get("meta", {}).get("last_updated")
                        if updated and (not last_updated or updated > last_updated):
                            last_updated = updated
                
                if entry_count > 0:
                    domain_stats[domain_name] = {
                        "total_entries": entry_count,
                        "last_updated": last_updated
                    }
                    domains.append(domain_name)
    
    combined_index = {
        "domain": "all",
        "combined": True,
        "domains_included": sorted(domains),
        "domain_statistics": domain_stats,
        "metadata": {
            "created": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "total_domains": len(domains),
            "total_entries": sum(s["total_entries"] for s in domain_stats.values())
        }
    }
    
    os.makedirs(os.path.dirname(combined_index_path) or ".", exist_ok=True)
    
    # IMPROVEMENT: Atomic write (temp file + rename) prevents JSON corruption on crash
    import tempfile
    temp_dir = os.path.dirname(combined_index_path) or "."
    with tempfile.NamedTemporaryFile(mode="w", dir=temp_dir, delete=False, encoding="utf-8", suffix=".tmp") as tmp:
        json.dump(combined_index, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    
    try:
        os.replace(tmp_path, combined_index_path)  # Atomic rename operation
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
