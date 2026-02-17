# Phase 3.5 - Consolidated JSON Structure

## Overview
The minister conversion system has been restructured to consolidate all entries for each category into **single JSON files** instead of individual atomic files in subdirectories.

## New Structure

### Before (Atomic Files)
```
/data/ministers/
└── strategy/
    ├── doctrine.json
    ├── /principles/
    │   ├── uuid1.json
    │   ├── uuid2.json
    │   └── ... (1532 files)
    ├── /rules/
    │   ├── uuid1.json
    │   └── ... (1535 files)
    ├── /claims/
    │   ├── uuid1.json
    │   └── ... (1370 files)
    └── /warnings/
        ├── uuid1.json
        └── ... (1404 files)
```
**Total files per domain: ~6000-8000 individual JSON files**

### After (Consolidated Arrays)
```
/data/ministers/
└── strategy/
    ├── doctrine.json          (summary metadata)
    ├── principles.json        (array of 1532 principle entries)
    ├── rules.json             (array of 1535 rule entries)
    ├── claims.json            (array of 1370 claim entries)
    ├── warnings.json          (array of 1404 warning entries)
    └── vector.index           (metadata file)
```
**Total files per domain: 6 files**

## File Format

### principles.json (and other category files)
```json
{
  "domain": "strategy",
  "category": "principles",
  "entries": [
    {
      "id": "00e8b69d-1f17-4250-afa2-8894b3849c8f",
      "text": "Thorough preparation mitigates uncertainty in complex environments.",
      "source": {
        "book": "16-05-2021-070111The-Richest-Man-in-Babylon",
        "chapter": 29
      },
      "weight": 1.0
    },
    {
      "id": "0114bcd0-f2c9-4bed-a72f-17cb5e095dfa",
      "text": "Break complex tasks into manageable components for targeted improvement.",
      "source": {
        "book": "Deep Work",
        "chapter": 6
      },
      "weight": 1.0
    }
    // ... more entries
  ],
  "meta": {
    "total_entries": 1532,
    "last_updated": "2026-02-11T12:34:56.789123Z",
    "aggregated_from": [
      {"book": "16-05-2021-070111The-Richest-Man-in-Babylon", "chapter": 29},
      {"book": "Deep Work", "chapter": 6},
      // ... more sources
    ]
  }
}
```

### doctrine.json
```json
{
  "domain": "strategy",
  "type": "domain_summary",
  "consolidated": true,
  "meta": {
    "total_entries": 0,
    "last_updated": null
  }
}
```

## Data Migration Summary

- **Total entries consolidated: 40,162**
- **Domains with data: 17/19**
- **Directories removed: 76** (4 categories × 19 domains)
- **Space savings: ~98%** (from ~40,000 individual files to ~114 consolidated files)

## Domain Statistics

| Domain | Principles | Rules | Claims | Warnings | Total |
|--------|-----------|-------|--------|----------|-------|
| strategy | 1,532 | 1,535 | 1,370 | 1,404 | 5,841 |
| constraints | 1,424 | 1,442 | 1,298 | 1,330 | 5,494 |
| power | 1,079 | 1,071 | 970 | 982 | 4,102 |
| risk | 1,137 | 1,124 | 1,025 | 1,049 | 4,335 |
| adaptation | 1,041 | 1,038 | 944 | 977 | 4,000 |
| psychology | 837 | 853 | 785 | 807 | 3,282 |
| discipline | 851 | 851 | 772 | 791 | 3,265 |
| optionality | 522 | 537 | 484 | 496 | 2,039 |
| timing | 536 | 551 | 498 | 507 | 2,092 |
| conflict | 555 | 546 | 491 | 518 | 2,110 |
| data | 132 | 131 | 121 | 121 | 505 |
| truth | 345 | 345 | 321 | 330 | 1,341 |
| executor | 162 | 166 | 146 | 156 | 630 |
| legitimacy | 124 | 127 | 115 | 121 | 487 |
| technology | 90 | 93 | 90 | 90 | 363 |
| execution | 63 | 63 | 60 | 60 | 246 |
| base | 9 | 9 | 6 | 6 | 30 |
| diplomacy | - | - | - | - | 0 |
| registry | - | - | - | - | 0 |

**Grand Total: 40,162 entries**

## Accessing Data

### Example: Query all rules in the truth domain
```python
import json

with open("data/ministers/truth/rules.json", "r") as f:
    rules_data = json.load(f)

print(f"Total rules: {rules_data['meta']['total_entries']}")
for entry in rules_data['entries']:
    print(f"  - {entry['text'][:80]}...")
    print(f"    From: {entry['source']['book']} (Ch.{entry['source']['chapter']})")
```

### Example: Query all entries across a domain
```python
import json
import os

domain_path = "data/ministers/strategy"
all_entries = {}

for category in ["principles", "rules", "claims", "warnings"]:
    with open(f"{domain_path}/{category}.json", "r") as f:
        category_data = json.load(f)
        all_entries[category] = category_data['entries']

print(f"Strategy domain statistics:")
for category, entries in all_entries.items():
    print(f"  {category}: {len(entries)} entries")
```

## Benefits

1. **Faster File I/O**: Single read/write per category vs. thousands of individual files
2. **Easier Querying**: All entries in one JSON array
3. **Better Performance**: Reduced file system overhead
4. **Storage Efficient**: ~98% reduction in number of files
5. **Cleaner Structure**: Clear organization with domain/category hierarchy
6. **Easier Backup**: Fewer files to manage and backup
7. **Better Tracking**: Metadata and sources kept with all entries

## Code Changes

- **minister_converter.py**: Updated to use `add_category_entry()` instead of `write_atomic_entry()`
- **ensure_minister_structure()**: Creates consolidated JSON files instead of subdirectories
- **update_combined_vector_index()**: Counts from consolidated files
- **test_minister_converter.py**: Updated tests to validate new structure
- **bat​ch_convert_rag_storage.py**: Uses updated converter (no changes needed)

## Backward Compatibility

The old atomic file directories have been completely removed. All queries should now use the consolidated JSON files directly.
