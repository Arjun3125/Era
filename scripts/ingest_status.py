#!/usr/bin/env python3
"""Comprehensive ingestion status report."""
import json, os
from pathlib import Path

print("=" * 70)
print("INGESTION STATUS REPORT")
print("=" * 70)

# Check books in data/ministers (successfully processed)
ministers_root = Path(r"c:\era\ingestion\data\ministers")
if ministers_root.exists():
    minister_dirs = len(list(ministers_root.glob("*/")))
    print(f"\nSuccessfully processed minister domains: {minister_dirs}")
    
    # Sample a domain to see structure
    for domain_dir in list(ministers_root.glob("*"))[:3]:
        if domain_dir.is_dir():
            files = list(domain_dir.glob("*.json"))
            print(f"  - {domain_dir.name}: {len(files)} files")

# Check vector_db_stub for actual stored vectors
vec_stub = Path(r"c:\era\data\vector_db_stub.json")
if vec_stub.exists():
    try:
        with open(vec_stub) as f:
            vec_data = json.load(f)
        combined = vec_data.get("combined", {})
        domains = vec_data.get("domains", {})
        
        print(f"\nVector storage:")
        print(f"  Combined vectors: {len(combined)}")
        print(f"  Domain vectors: {sum(len(v) for v in domains.values())}")
        
        # Check if vectors are real (non-zero)
        real_vectors = 0
        zero_vectors = 0
        for v in combined.values():
            if isinstance(v, dict) and "embedding" in v:
                emb = v["embedding"]
                if any(x != 0 for x in emb):
                    real_vectors += 1
                else:
                    zero_vectors += 1
        
        print(f"  Real vectors: {real_vectors} (non-zero)")
        print(f"  Zero vectors: {zero_vectors} (fallback)")
    except Exception as e:
        print(f"Error reading vector_db_stub: {e}")

# Check rag_storage for doctrine files
print(f"\nRag storage books with doctrine:")
rag_root = Path(r"c:\era\rag_storage")
if rag_root.exists():
    for book_dir in rag_root.glob("*/"):
        doctrine_file = book_dir / "02_doctrine_chunks.json"
        if doctrine_file.exists():
            try:
                with open(doctrine_file) as f:
                    data = json.load(f)
                    chapters = list(data.values()) if isinstance(data, dict) else list(data)
                    total_items = sum(len(c.get("principles", []))+len(c.get("rules", []))+len(c.get("claims", []))+len(c.get("warnings", [])) for c in chapters)
                    print(f"  - {book_dir.name}: {len(chapters)} chapters, {total_items} total doctrine items")
            except Exception as e:
                print(f"  - {book_dir.name}: error reading ({e})")

print("\n" + "=" * 70)
