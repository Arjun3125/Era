#!/usr/bin/env python3
"""Check successful ingestions with doctrine and embeddings."""
import os, json
from pathlib import Path

root = Path(r"c:\era\rag_storage")
if not root.exists():
    print("No rag_storage found")
    exit(0)

dirs = sorted([d for d in root.iterdir() if d.is_dir()])
print(f"Total books in rag_storage: {len(dirs)}\n")

completed = 0
with_doctrine = 0
with_embeddings = 0

for d in dirs:
    has_doctrine = (d / "02_doctrine_chunks.json").exists()
    has_embed = (d / "03_embeddings.json").exists()
    progress_file = d / "progress.json"
    is_completed = False
    
    if progress_file.exists():
        try:
            with open(progress_file) as f:
                prog = json.load(f)
                is_completed = prog.get("current_phase") == "completed" or prog.get("phase") == "completed"
        except:
            pass
    
    if is_completed:
        completed += 1
    if has_doctrine:
        with_doctrine += 1
    if has_embed:
        with_embeddings += 1

print(f"Completed ingestions: {completed}/{len(dirs)}")
print(f"With doctrine files: {with_doctrine}/{len(dirs)}")
print(f"With embeddings: {with_embeddings}/{len(dirs)}")
print(f"\nCompletion rate: {completed*100//len(dirs)}%")
