#!/usr/bin/env python3
"""
Migrate atomic entry files to consolidated category JSON files.
Converts the old structure (atomic files in subdirectories) to the new structure
(consolidated array JSON files per category).
"""
import json
import os
import sys
from pathlib import Path

def migrate_domain(domain_path: str) -> dict:
    """
    Migrate a single domain from atomic files to consolidated structure.
    
    Args:
        domain_path: Path to the domain folder (e.g., /data/ministers/strategy)
    
    Returns:
        Statistics about the migration
    """
    domain_name = os.path.basename(domain_path)
    stats = {
        "domain": domain_name,
        "entries_migrated": 0,
        "categories_processed": 0,
        "errors": []
    }
    
    # For each category, consolidate atomic files
    for category in ["principles", "rules", "claims", "warnings"]:
        category_dir = os.path.join(domain_path, category)
        category_file = os.path.join(domain_path, f"{category}.json")
        
        # Skip if directory doesn't exist (empty category)
        if not os.path.isdir(category_dir):
            continue
        
        # Initialize consolidated file
        consolidated_data = {
            "domain": domain_name,
            "category": category,
            "entries": [],
            "meta": {
                "total_entries": 0,
                "last_updated": None,
                "aggregated_from": []
            }
        }
        
        # Read all atomic files in the directory
        atomic_files = [f for f in os.listdir(category_dir) if f.endswith('.json')]
        
        for atomic_file in atomic_files:
            atomic_path = os.path.join(category_dir, atomic_file)
            try:
                with open(atomic_path, "r", encoding="utf-8") as f:
                    entry_data = json.load(f)
                
                # Extract the entry
                entry = {
                    "id": entry_data.get("id"),
                    "text": entry_data.get("text"),
                    "source": entry_data.get("source", {}),
                    "weight": entry_data.get("weight", 1.0)
                }
                
                consolidated_data["entries"].append(entry)
                
                # Track source
                source = entry_data.get("source", {})
                source_key = {"book": source.get("book"), "chapter": source.get("chapter")}
                if source_key not in consolidated_data["meta"]["aggregated_from"]:
                    consolidated_data["meta"]["aggregated_from"].append(source_key)
                
                stats["entries_migrated"] += 1
            except Exception as e:
                stats["errors"].append(f"Error reading {atomic_file}: {str(e)}")
        
        # Update metadata
        consolidated_data["meta"]["total_entries"] = len(consolidated_data["entries"])
        if consolidated_data["entries"]:
            consolidated_data["meta"]["last_updated"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
        
        # Write consolidated file
        with open(category_file, "w", encoding="utf-8") as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        
        stats["categories_processed"] += 1
        
        # Remove the old atomic files directory
        # (keep it for safety during testing, can be removed later)
        # shutil.rmtree(category_dir)
        print(f"[OK] Consolidated {category}: {len(consolidated_data['entries'])} entries")
    
    return stats

def main():
    """Migrate all domains in the minister structure."""
    data_root = "data"
    ministers_root = os.path.join(data_root, "ministers")
    
    if not os.path.exists(ministers_root):
        print(f"[ERROR] Ministers directory not found: {ministers_root}")
        sys.exit(1)
    
    print(f"Starting migration from {ministers_root}")
    print("-" * 60)
    
    all_stats = {
        "total_domains": 0,
        "total_entries_migrated": 0,
        "domain_results": []
    }
    
    # Process each domain
    for domain_name in sorted(os.listdir(ministers_root)):
        domain_path = os.path.join(ministers_root, domain_name)
        if os.path.isdir(domain_path):
            print(f"\nMigrating domain: {domain_name}")
            stats = migrate_domain(domain_path)
            all_stats["domain_results"].append(stats)
            all_stats["total_entries_migrated"] += stats["entries_migrated"]
            all_stats["total_domains"] += 1
    
    # Update combined index
    print("\n" + "-" * 60)
    print("Updating combined vector index...")
    
    combined_index_path = os.path.join(data_root, "combined_vector.index")
    domains = []
    domain_stats = {}
    
    for domain_name in sorted(os.listdir(ministers_root)):
        domain_path = os.path.join(ministers_root, domain_name)
        if os.path.isdir(domain_path):
            entry_count = 0
            last_updated = None
            
            for category in ["principles", "rules", "claims", "warnings"]:
                category_file = os.path.join(domain_path, f"{category}.json")
                
                if os.path.exists(category_file):
                    with open(category_file, "r", encoding="utf-8") as f:
                        category_data = json.load(f)
                    
                    entries = category_data.get("entries", [])
                    entry_count += len(entries)
                    
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
    
    with open(combined_index_path, "w", encoding="utf-8") as f:
        json.dump(combined_index, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Total domains processed: {all_stats['total_domains']}")
    print(f"Total entries migrated: {all_stats['total_entries_migrated']}")
    print(f"Combined index: {combined_index['metadata']['total_entries']} total entries")
    print(f"Domains with data: {len(domains)}")
    
    # Report any errors
    total_errors = sum(len(d["errors"]) for d in all_stats["domain_results"])
    if total_errors > 0:
        print(f"\n[WARNING] {total_errors} errors encountered:")
        for result in all_stats["domain_results"]:
            if result["errors"]:
                for error in result["errors"]:
                    print(f"  {error}")

if __name__ == "__main__":
    main()
