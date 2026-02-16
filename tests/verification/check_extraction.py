#!/usr/bin/env python3
"""Check extraction results."""
import json

data = json.load(open(r'c:\era\rag_storage\16-05-2021-070111The-Richest-Man-in-Babylon\02_doctrine_chunks.json'))
print(f'Data structure type: {type(data)}')
print(f'Data keys (first 10): {list(data.keys())[:10] if isinstance(data, dict) else "N/A"}')
print(f'Total entries: {len(data)}')
print(f'\nFirst 5 chapters summary:')
chapters_list = list(data.values()) if isinstance(data, dict) else data
for i, ch in enumerate(chapters_list[:5]):
    p = len(ch.get('principles', []))
    r = len(ch.get('rules', []))
    c = len(ch.get('claims', []))
    w = len(ch.get('warnings', []))
    d = ch.get('domains', [])
    print(f'  Chapter {i+1}: {p} principles | {r} rules | {c} claims | {w} warnings | domains: {d}')
    if p > 0:
        print(f'    Sample principle: {ch["principles"][0][:60]}...')
    if r > 0:
        print(f'    Sample rule: {ch["rules"][0][:60]}...')

print(f'\nTotal extracted items:')
total_p = sum(len(ch.get('principles', [])) for ch in chapters_list)
total_r = sum(len(ch.get('rules', [])) for ch in chapters_list)
total_c = sum(len(ch.get('claims', [])) for ch in chapters_list)
total_w = sum(len(ch.get('warnings', [])) for ch in chapters_list)
print(f'  {total_p} principles | {total_r} rules | {total_c} claims | {total_w} warnings')
