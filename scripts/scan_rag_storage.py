#!/usr/bin/env python3
"""Scan rag_storage directories and summarize doctrine extraction counts."""
import os, json
from pathlib import Path

root = Path(r"c:\era\rag_storage")
if not root.exists():
    print("No rag_storage directory found")
    raise SystemExit(0)

dirs = sorted([d for d in root.iterdir() if d.is_dir()])
print(f"Found {len(dirs)} books in rag_storage (showing up to 50)")
print()

def summarize_doctrine(path):
    f = path / "02_doctrine_chunks.json"
    if not f.exists():
        return None
    try:
        data = json.load(open(f, "r", encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}
    # data may be dict mapping chapter_key -> parsed
    chapters = list(data.values()) if isinstance(data, dict) else list(data)
    total_chapters = len(chapters)
    total_p = sum(len(c.get("principles", [])) for c in chapters)
    total_r = sum(len(c.get("rules", [])) for c in chapters)
    total_c = sum(len(c.get("claims", [])) for c in chapters)
    total_w = sum(len(c.get("warnings", [])) for c in chapters)
    chapters_with_any = sum(1 for c in chapters if any(len(c.get(k, []))>0 for k in ("principles","rules","claims","warnings")))
    return {
        "chapters": total_chapters,
        "principles": total_p,
        "rules": total_r,
        "claims": total_c,
        "warnings": total_w,
        "chapters_with_any": chapters_with_any,
    }

for d in dirs[:50]:
    s = summarize_doctrine(d)
    if s is None:
        print(f"{d.name}: no doctrine file")
    elif isinstance(s, dict) and s.get("error"):
        print(f"{d.name}: error reading doctrine file: {s['error']}")
    else:
        pct = (s['chapters_with_any'] / s['chapters']*100) if (s['chapters']>0) else 0
        print(f"{d.name}: chapters={s['chapters']} | principles={s['principles']} rules={s['rules']} claims={s['claims']} warnings={s['warnings']} | chapters_with_any={s['chapters_with_any']} ({pct:.0f}%)")

print('\nDone.')
