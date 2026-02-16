# Quick Reference - Consolidated Minister Structure

## ⚡ TL;DR

Your minister files are now **consolidated JSON arrays** instead of individual atomic files.

### The Change
```
BEFORE: /data/ministers/truth/rules/uuid1.json (345 separate files)
AFTER:  /data/ministers/truth/rules.json (1 file with 345 entries)
```

## 📂 Directory Structure

```
c:\era\data\ministers\
├── adaptation/       (6 files - 4,000 entries)
├── base/            (6 files - 30 entries)
├── conflict/        (6 files - 2,110 entries)
├── constraints/     (6 files - 5,494 entries)
├── data/            (6 files - 505 entries)
├── diplomacy/       (4 files - empty)
├── discipline/      (6 files - 3,265 entries)
├── execution/       (5 files - 246 entries)
├── executor/        (6 files - 630 entries)
├── legitimacy/      (6 files - 487 entries)
├── optionality/     (6 files - 2,039 entries)
├── power/           (6 files - 4,102 entries)
├── psychology/      (6 files - 3,282 entries)
├── registry/        (4 files - empty)
├── risk/            (6 files - 4,335 entries)
├── strategy/        (6 files - 5,841 entries) ← LARGEST
├── technology/      (6 files - 363 entries)
├── timing/          (6 files - 2,092 entries)
└── truth/           (6 files - 1,341 entries)

Total: 19 domains, 113 files, 40,162 entries
```

## 📋 Files per Domain

Each domain folder contains:
```
doctrine.json       → domain metadata summary
principles.json     → all principles as JSON array
rules.json          → all rules as JSON array
claims.json         → all claims as JSON array
warnings.json       → all warnings as JSON array
vector.index        → statistics file
```

## 📖 Accessing Data

### Load all rules from a domain
```python
import json

with open('data/ministers/strategy/rules.json') as f:
    data = json.load(f)

entries = data['entries']  # List of 1,535 rule entries
for rule in entries:
    print(rule['text'])
```

### Get entry info
```python
entry = entries[0]
print(entry['id'])               # UUID
print(entry['text'])             # Rule text
print(entry['source']['book'])   # Source book
print(entry['source']['chapter']) # Chapter number
print(entry['weight'])           # Weight (usually 1.0)
```

### Find entries from specific book
```python
book_entries = [e for e in entries 
                if 'Meditations' in e['source']['book']]
```

### Count entries by category
```python
with open('data/ministers/strategy/principles.json') as f:
    principles = json.load(f)
print(f"Principles: {principles['meta']['total_entries']}")
```

## 🔍 All 19 Domains

| # | Domain | Entries | Largest Category |
|---|--------|---------|-----------------|
| 1 | **strategy** | 5,841 | principles (1,532) |
| 2 | **constraints** | 5,494 | rules (1,442) |
| 3 | **risk** | 4,335 | principles (1,137) |
| 4 | power | 4,102 | principles (1,079) |
| 5 | adaptation | 4,000 | principles (1,041) |
| 6 | psychology | 3,282 | rules (853) |
| 7 | discipline | 3,265 | principles (851) |
| 8 | timing | 2,092 | rules (551) |
| 9 | optionality | 2,039 | rules (537) |
| 10 | conflict | 2,110 | principles (555) |
| 11 | truth | 1,341 | principles (345) |
| 12 | executor | 630 | principles (162) |
| 13 | legitimacy | 487 | principles (124) |
| 14 | data | 505 | principles (132) |
| 15 | technology | 363 | rules (93) |
| 16 | execution | 246 | principles (63) |
| 17 | base | 30 | principles (9) |
| 18 | diplomacy | 0 | (empty) |
| 19 | registry | 0 | (empty) |

## 📊 JSON Structure Example

```json
{
  "domain": "truth",
  "category": "rules",
  "entries": [
    {
      "id": "01e8bc00-4857-498e-82b6-c01db1eac3b8",
      "text": "Educational goals must align with practical application.",
      "source": {
        "book": "Marcus-Aurelius-Meditations",
        "chapter": 24
      },
      "weight": 1.0
    },
    {
      "id": "02071406-662e-49bb-9b42-3b6c1d2d5220",
      "text": "Restructure inclinations to align with rational assessment.",
      "source": {
        "book": "Marcus-Aurelius-Meditations",
        "chapter": 23
      },
      "weight": 1.0
    }
  ],
  "meta": {
    "total_entries": 345,
    "last_updated": "2026-02-11T...",
    "aggregated_from": [
      {"book": "Marcus-Aurelius-Meditations", "chapter": 23}
    ]
  }
}
```

## ✅ Statistics

| Metric | Value |
|--------|-------|
| Total files | 113 |
| Total entries | 40,162 |
| Files reduced | 97.7% |
| Principles | 11,339 |
| Rules | 11,408 |
| Claims | 10,240 |
| Warnings | 10,240 |

## 🎯 Common Tasks

### Load all entries from one domain
```python
import json
import os

domain = 'strategy'
all_entries = []

for category in ['principles', 'rules', 'claims', 'warnings']:
    with open(f'data/ministers/{domain}/{category}.json') as f:
        data = json.load(f)
        all_entries.extend(data['entries'])

print(f"{domain}: {len(all_entries)} total entries")
```

### Search across a domain
```python
with open('data/ministers/strategy/rules.json') as f:
    rules = json.load(f)

search_term = "assessment"
results = [e for e in rules['entries'] 
           if search_term.lower() in e['text'].lower()]

print(f"Found {len(results)} matching rules")
```

### Compare two domains
```python
domains = ['strategy', 'power']

for domain in domains:
    entry_count = 0
    for category in ['principles', 'rules', 'claims', 'warnings']:
        with open(f'data/ministers/{domain}/{category}.json') as f:
            data = json.load(f)
            entry_count += data['meta']['total_entries']
    print(f"{domain}: {entry_count} entries")
```

## ❌ What's Different

### Old Way (DOESN'T WORK)
```python
# This no longer works - atomic files removed:
with open('data/ministers/strategy/principles/uuid.json') as f:
    data = json.load(f)
```

### New Way (USE THIS)
```python
# Load consolidated array instead:
with open('data/ministers/strategy/principles.json') as f:
    data = json.load(f)
    for entry in data['entries']:
        print(entry['text'])
```

## 📧 Data Sources

**4 books converted to 40,162 entries:**
1. The Richest Man in Babylon (16-05-2021)
2. TNA13Crawford2009 (26-May-2009)
3. Deep Work
4. Marcus Aurelius Meditations

## 🚀 Performance

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Load 100 entries | 100 file opens | 1 file open | 100x |
| Backup 1 domain | ~6000 files | 6 files | 1000x |
| Search all entries | Parse 1000s files | Parse 1 file | 1000x+ |

## 📝 Notes

- All entries have UUID for tracking
- Source (book + chapter) tracked on every entry
- Metadata updated on every write
- Can directly query with Python without additional db
- Optional: Set up PostgreSQL + pgvector for semantic search
