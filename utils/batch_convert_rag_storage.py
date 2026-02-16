"""
Batch convert all doctrines from rag_storage into minister structure.
"""

import json
import os
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add ingestion src to path
ingestion_src = os.path.join(os.path.dirname(__file__), "ingestion", "v2", "src")
if ingestion_src not in sys.path:
    sys.path.insert(0, ingestion_src)

from minister_converter import convert_all_doctrines, update_combined_vector_index


def batch_convert_rag_storage(rag_storage_path: str = "rag_storage", data_root: str = "data"):
    """
    Convert all doctrine.json files from rag_storage into minister structure.
    
    Args:
        rag_storage_path: Path to rag_storage directory
        data_root: Target data root directory
    """
    
    rag_path = Path(rag_storage_path)
    if not rag_path.exists():
        print(f"Error: {rag_storage_path} not found")
        return
    
    print("=" * 80)
    print("BATCH CONVERTING RAG_STORAGE DOCTRINES TO MINISTER STRUCTURE")
    print("=" * 80)
    
    books_processed = 0
    total_entries_created = 0
    all_domain_stats = {}
    
    # Find all 02_doctrine.json files
    doctrine_files = sorted(rag_path.glob("*/02_doctrine.json"))
    
    if not doctrine_files:
        print("No doctrine files found in rag_storage")
        return
    
    print(f"\nFound {len(doctrine_files)} books with doctrine data\n")
    
    for doctrine_file in doctrine_files:
        book_dir = doctrine_file.parent
        book_slug = book_dir.name
        
        print(f"\n[{books_processed + 1}] Processing: {book_slug}")
        print("-" * 80)
        
        try:
            # Load doctrine
            with open(doctrine_file, "r", encoding="utf-8") as f:
                doctrines = json.load(f)
            
            if not isinstance(doctrines, list):
                print(f"⚠ Warning: doctrine file is not a list, skipping")
                continue
            
            print(f"  Loaded {len(doctrines)} chapters")
            
            # Convert to minister structure
            def progress_callback(**kw):
                if kw.get("message"):
                    print(f"  • {kw['message']}", end="\r")
            
            summary = convert_all_doctrines(
                doctrines,
                book_slug=book_slug,
                data_root=data_root,
                progress_cb=progress_callback
            )
            
            print(f"\n  [OK] Conversion complete:")
            print(f"    - Chapters processed: {summary['total_chapters_processed']}")
            print(f"    - Entries created: {summary['total_entries_created']}")
            print(f"    - Domains populated: {summary['domains_populated']}")
            
            # Aggregate statistics
            books_processed += 1
            total_entries_created += summary['total_entries_created']
            
            for domain, count in summary['domain_statistics'].items():
                if domain not in all_domain_stats:
                    all_domain_stats[domain] = 0
                all_domain_stats[domain] += count
            
        except Exception as e:
            print(f"  [ERROR] Error processing {book_slug}: {e}")
            import traceback
            traceback.print_exc()
    
    # Update combined index
    print(f"\n{'-' * 80}")
    print("Updating combined vector index...")
    print(f"{'-' * 80}")
    
    try:
        update_combined_vector_index(data_root=data_root)
        print("[OK] Combined index updated")
    except Exception as e:
        print(f"[ERROR] Error updating combined index: {e}")
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("BATCH CONVERSION SUMMARY")
    print(f"{'=' * 80}")
    print(f"Books processed: {books_processed}")
    print(f"Total entries created: {total_entries_created}")
    print(f"Total domains populated: {len(all_domain_stats)}")
    
    print("\nDomain statistics:")
    for domain in sorted(all_domain_stats.keys()):
        count = all_domain_stats[domain]
        print(f"  {domain:15} {count:4} entries")
    
    print(f"\n{'=' * 80}")
    print("[OK] Batch conversion complete!")
    print(f"{'=' * 80}\n")
    
    return {
        "books_processed": books_processed,
        "total_entries_created": total_entries_created,
        "domain_statistics": all_domain_stats
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch convert RAG storage to minister structure")
    parser.add_argument("--rag-storage", default="rag_storage", help="Path to rag_storage")
    parser.add_argument("--data-root", default="data", help="Path to data root")
    
    args = parser.parse_args()
    
    summary = batch_convert_rag_storage(
        rag_storage_path=args.rag_storage,
        data_root=args.data_root
    )
