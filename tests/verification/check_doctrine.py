#!/usr/bin/env python3
"""Check doctrine extraction."""
import json
path = r'c:\era\rag_storage\16-05-2021-070111The-Richest-Man-in-Babylon\02_doctrine_chunks.json'
try:
    data = json.load(open(path, encoding='utf-8'))
    chapters = list(data.values()) if isinstance(data, dict) else list(data)
    print(f'Total chapters: {len(chapters)}')
    
    total_p = sum(len(c.get('principles', [])) for c in chapters)
    total_r = sum(len(c.get('rules', [])) for c in chapters)
    total_c = sum(len(c.get('claims', [])) for c in chapters)
    total_w = sum(len(c.get('warnings', [])) for c in chapters)
    
    print(f'Total principles: {total_p}')
    print(f'Total rules: {total_r}')
    print(f'Total claims: {total_c}')
    print(f'Total warnings: {total_w}')
    print(f'Grand total: {total_p + total_r + total_c + total_w}')
    
    if total_p > 0:
        ch = chapters[0]
        print(f'\nSample principles from first chapter:')
        for p in ch.get('principles', [])[:2]:
            print(f'  - {p}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
