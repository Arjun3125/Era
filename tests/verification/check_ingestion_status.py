#!/usr/bin/env python3
"""Check doctrine extraction across all books."""
import json
import os
from pathlib import Path

root = Path(r"c:\era\ingestion\v2\rag_storage")
books = sorted([d for d in root.iterdir() if d.is_dir()])

print(f"Total books ingested: {len(books)}")
print()

total_p = 0
total_r = 0
total_c = 0
total_w = 0
books_with_any = 0

for book in books[:10]:  # Check first 10
    doc_path = book / "02_doctrine_chunks.json"
    if not doc_path.exists():
        continue
    
    try:
        data = json.load(open(doc_path, encoding='utf-8'))
        chapters = list(data.values()) if isinstance(data, dict) else list(data)
        
        p = sum(len(c.get('principles', [])) for c in chapters)
        r = sum(len(c.get('rules', [])) for c in chapters)
        c_val = sum(len(c.get('claims', [])) for c in chapters)
        w = sum(len(c.get('warnings', [])) for c in chapters)
        
        total_p += p
        total_r += r
        total_c += c_val
        total_w += w
        
        if any([p, r, c_val, w]):
            books_with_any += 1
            print(f"{book.name}: P={p} R={r} C={c_val} W={w} ✓")
        else:
            print(f"{book.name}: P={p} R={r} C={c_val} W={w} (empty)")
            
    except Exception as e:
        print(f"{book.name}: ERROR reading - {e}")

print()
print(f"First 10 books TOTALS: P={total_p} R={total_r} C={total_c} W={total_w}")
print(f"Books with any extraction: {books_with_any}/10")
