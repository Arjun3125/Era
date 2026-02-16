# Phase 3.5 Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Automatic (Recommended)

Run the full ingestion pipeline - Phase 3.5 executes automatically:

```bash
cd /era/ingestion/v2
python -m src.ingest_pipeline /path/to/your/book.pdf
```

That's it! Phase 3.5 runs after embeddings complete. Check the output:

```
[INGEST] Phase 3.5: Minister Conversion ⭐
  ✓ Converted 9 chapters
  ✓ Created 247 entries
  ✓ Updated combined index
```

### Option 2: Manual/Programmatic

```python
import json
from src.minister_converter import convert_all_doctrines

# Load chapter doctrines from Phase 2
with open("rag_storage/MyBook2026/02_doctrine.json") as f:
    doctrines = json.load(f)

# Convert to minister structure
summary = convert_all_doctrines(
    doctrines,
    book_slug="MyBook2026",
    data_root="data"
)

print(f"✓ Created {summary['total_entries_created']} entries")
print(f"✓ Populated {summary['domains_populated']} domains")
```

---

## 📁 What Gets Created

After Phase 3.5 completes, your `/data/` folder contains:

```
/data/ministers/
├── /adaptation/
│   ├── doctrine.json           (Summary of all entries)
│   ├── /principles/            (Individual principle files)
│   ├── /rules/
│   ├── /claims/
│   └── /warnings/
├── /constraints/
├── /psychology/
├── /risk/
... (18 domains total)
└── combined_vector.index       (Cross-domain aggregation)
```

---

## 🔍 How to Query the Data

### List all principles in constraints domain:

```python
import json
from pathlib import Path

domain = "constraints"
principles_dir = Path(f"data/ministers/{domain}/principles")

for uuid_file in principles_dir.glob("*.json"):
    with open(uuid_file) as f:
        entry = json.load(f)
    print(f"- {entry['text']}")
```

### Get domain statistics:

```python
import json

with open("data/combined_vector.index") as f:
    index = json.load(f)

# See stats for all domains
for domain, stats in index["domain_statistics"].items():
    print(f"{domain}: {stats['total_entries']} entries")

# Total across all
total = index["metadata"]["total_entries"]
print(f"\nTotal entries: {total}")
```

### Load all entries from a specific domain:

```python
import json
from pathlib import Path

domain = "power"
with open(f"data/ministers/{domain}/doctrine.json") as f:
    doctrine = json.load(f)

# Access aggregated entries
all_principles = doctrine["principles"]
all_rules = doctrine["rules"]
all_claims = doctrine["claims"]
all_warnings = doctrine["warnings"]

print(f"Domain: {doctrine['domain']}")
print(f"Total entries: {doctrine['meta']['total_entries']}")
print(f"Sources: {doctrine['aggregated_from']}")
```

---

## 📊 Understanding the Data Structures

### Atomic Entry File

**Location:** `/data/ministers/{domain}/{category}/{uuid}.json`

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "text": "Operational effectiveness is improved through direct engagement with physical systems.",
  "source": {
    "book": "TNA13Crawford2009",
    "chapter": 1
  },
  "weight": 1.0,
  "vector_id": null
}
```

**Fields:**
- `id`: Unique identifier (UUID)
- `text`: The extracted principle/rule/claim/warning
- `source.book`: Which book it came from
- `source.chapter`: Which chapter
- `weight`: Importance (1.0 = normal)
- `vector_id`: Link to embedding (when vectors are computed)

### Domain Summary File

**Location:** `/data/ministers/{domain}/doctrine.json`

```json
{
  "domain": "constraints",
  "aggregated_from": [
    {"book": "TNA13Crawford2009", "chapter": 1},
    {"book": "TNA13Crawford2009", "chapter": 3},
    {"book": "DeepWork", "chapter": 5}
  ],
  "principles": [
    {"id": "uuid1", "text": "..."},
    {"id": "uuid2", "text": "..."}
  ],
  "rules": [...],
  "claims": [...],
  "warnings": [...],
  "meta": {
    "total_entries": 47,
    "last_updated": "2026-02-11T12:52:27Z"
  }
}
```

**Purpose:**
- Quick access to all entries in a domain
- Source tracking (which books contributed)
- Metadata (count, timestamp)

### Combined Index

**Location:** `/data/combined_vector.index`

```json
{
  "domain": "all",
  "combined": true,
  "domains_included": [
    "adaptation", "base", "conflict", ..., "truth"
  ],
  "domain_statistics": {
    "adaptation": {
      "total_entries": 23,
      "last_updated": "2026-02-11T12:52:27Z"
    },
    "constraints": {
      "total_entries": 47,
      "last_updated": "2026-02-11T12:52:27Z"
    },
    ...
  },
  "metadata": {
    "created": "2026-02-11T12:52:27Z",
    "total_domains": 18,
    "total_entries": 1247
  }
}
```

**Purpose:**
- Single source of truth for all domain statistics
- See how many entries each domain has
- Cross-domain aggregation metadata

---

## 💻 Common Operations

### Count entries by domain

```python
import json

with open("data/combined_vector.index") as f:
    index = json.load(f)

stats = index["domain_statistics"]
sorted_domains = sorted(stats.items(), key=lambda x: x[1]["total_entries"], reverse=True)

for domain, info in sorted_domains[:5]:
    print(f"{domain}: {info['total_entries']} entries")
```

### Find entries from a specific book

```python
import json
from pathlib import Path

book = "TNA13Crawford2009"
found_entries = []

# Search all domain doctrine.json files
for domain_dir in Path("data/ministers").iterdir():
    if not domain_dir.is_dir():
        continue
    
    doctrine_file = domain_dir / "doctrine.json"
    if not doctrine_file.exists():
        continue
    
    with open(doctrine_file) as f:
        doctrine = json.load(f)
    
    for entry in doctrine["aggregated_from"]:
        if entry["book"] == book:
            found_entries.append(doctrine["domain"])
            break

print(f"'{book}' contributed to domains: {found_entries}")
```

### Export all entries to CSV

```python
import json
import csv
from pathlib import Path

with open("all_entries.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["domain", "category", "id", "text", "book", "chapter", "weight"])
    
    for domain_dir in Path("data/ministers").iterdir():
        if not domain_dir.is_dir():
            continue
        
        domain = domain_dir.name
        
        for category in ["principles", "rules", "claims", "warnings"]:
            cat_dir = domain_dir / category
            if not cat_dir.exists():
                continue
            
            for entry_file in cat_dir.glob("*.json"):
                with open(entry_file) as f:
                    entry = json.load(f)
                
                writer.writerow([
                    domain,
                    category,
                    entry["id"],
                    entry["text"],
                    entry["source"]["book"],
                    entry["source"]["chapter"],
                    entry["weight"]
                ])

print("✓ Exported all_entries.csv")
```

---

## 🗄️ Optional: PostgreSQL Integration

If you want full-text and semantic search, set up PostgreSQL:

```bash
# Install dependencies
pip install psycopg2-binary pgvector-python sentence-transformers

# Create database
createdb minister_db
psql minister_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Initialize schema:

```python
from src.minister_vector_db import MinisterVectorDB

db = MinisterVectorDB("postgresql://user:password@localhost/minister_db")
db.init_schema()
print("✓ Database initialized")
```

Now you can do semantic search:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
query = "How do constraints affect strategy?"
query_vector = model.encode(query)

# Search across all domains
results = db.search_combined(query_vector, limit=10)
for r in results:
    print(f"{r['domain']}/{r['category']}: {r['text'][:60]}... (distance: {r['distance']:.3f})")
```

Or search within a domain:

```python
results = db.search_by_domain("constraints", query_vector, limit=5)
```

---

## ⚠️ Troubleshooting

### Phase 3.5 failed but ingestion continued

Check the error log:
```bash
cat rag_storage/MyBook2026/03_5_minister_errors.log
```

Common issues:
- File permissions on `/data/` directory
- Disk space (shouldn't happen unless disk is full)
- Invalid JSON in Phase 2 output

### Combined index is empty

Run update manually:
```python
from src.minister_converter import update_combined_vector_index
update_combined_vector_index(data_root="data")
print("✓ Index updated")
```

### No entries appear for a domain

Check if the domain was assigned:
```bash
cat rag_storage/MyBook2026/02_doctrine.json | grep -A 5 "domains"
```

If domains are assigned but no entries appear:
```bash
ls -la data/ministers/{domain}/principles/
```

---

## 📈 Performance Notes

- **Small book (50 pages):** Phase 3.5 takes <1 second
- **Medium book (200 pages):** ~2-3 seconds
- **Large book (500+ pages):** ~5-10 seconds

Memory footprint is minimal because entries are streamed to disk.

---

## 📚 Learn More

- **Full Architecture:** [PHASE_3_5_MINISTER_CONVERSION.md](PHASE_3_5_MINISTER_CONVERSION.md)
- **Implementation Details:** [PHASE_3_5_IMPLEMENTATION_SUMMARY.md](PHASE_3_5_IMPLEMENTATION_SUMMARY.md)

---

**Ready to go!** Start by running the ingestion pipeline and Phase 3.5 will handle everything automatically. 🚀
