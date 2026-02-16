#!/usr/bin/env python3
"""Check what chapter text looks like."""
import json
from pathlib import Path

book = Path(r"C:\era\ingestion\v2\rag_storage\16-05-2021-070111The-Richest-Man-in-Babylon")
chap_file = book / "01_chapters.json"

if chap_file.exists():
    try:
        data = json.load(open(chap_file, encoding='utf-8'))
        chapters = list(data.values()) if isinstance(data, dict) else data
        
        print(f"Total chapters: {len(chapters)}")
        if len(chapters) > 0:
            ch = chapters[0]
            text = ch.get('text', ch.get('raw_text', ''))
            print(f"\nFirst chapter keys: {list(ch.keys())}")
            print(f"First chapter text length: {len(text)}")
            print(f"\nFirst 600 chars of text:")
            print(text[:600])
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No chapters file")
