# Phase 3.5: Minister Conversion System

**Status:** Implemented and integrated into the ingestion pipeline

## Overview

Phase 3.5 converts extracted doctrine from Phase 2 into a domain-specific minister structure organized by 18 operational domains. This creates an atomic, queryable knowledge base that bridges tactical extracted doctrine and strategic vector embeddings.

## Architecture

### File Structure

```
/data/
├── /books/                          # Original PDFs
├── /ministers/                      # Domain-organized doctrine
│   ├── /adaptation/
│   │   ├── doctrine.json            # Summary & aggregation
│   │   ├── vector.index             # Domain-specific vectors
│   │   ├── /principles/
│   │   │   ├── uuid.json
│   │   │   └── ...
│   │   ├── /rules/
│   │   │   ├── uuid.json
│   │   │   └── ...
│   │   ├── /claims/
│   │   │   ├── uuid.json
│   │   │   └── ...
│   │   └── /warnings/
│   │       ├── uuid.json
│   │       └── ...
│   ├── /base/
│   ├── /conflict/
│   ├── /constraints/
│   ├── /data/
│   ├── /diplomacy/
│   ├── /discipline/
│   ├── /executor/
│   ├── /legitimacy/
│   ├── /optionality/
│   ├── /power/
│   ├── /psychology/
│   ├── /registry/
│   ├── /risk/
│   ├── /strategy/
│   ├── /technology/
│   ├── /timing/
│   └── /truth/
└── /combined_vector.index           # Cross-domain aggregation
```

### Domain List (18 Domains)

1. **adaptation** - Change management, flexibility, evolution
2. **base** - Foundation, grounding, core position
3. **conflict** - Opposition, competitive dynamics, clash
4. **constraints** - Limitations, boundaries, restrictions
5. **data** - Information, intelligence, signals
6. **diplomacy** - Negotiation, treaty, relationship management
7. **discipline** - Order, training, enforcement
8. **executor** - Implementation, agency, action
9. **legitimacy** - Authority, trust, justification
10. **optionality** - Choices, flexibility, alternatives
11. **power** - Force, influence, control
12. **psychology** - Morale, motivation, perception
13. **registry** - Recording, documentation, accountability
14. **risk** - Danger, hazard, uncertainty
15. **strategy** - Planning, long-term positioning
16. **technology** - Tools, systems, capability
17. **timing** - Rhythm, tempo, sequencing
18. **truth** - Verification, facts, reality check

## Phase 3.5 Execution Flow

### Entry Point

```python
from ingestion.v2.src.minister_converter import convert_all_doctrines

# After Phase 3 (embeddings) completes:
conversion_summary = convert_all_doctrines(
    doctrines,           # List of Chapter doctrine objects
    book_slug=book_id,   # Source book identifier
    data_root="data"     # Target directory
)
```

### Pseudocode Flow

```
Phase 3.5 Minister Conversion
├── For each chapter_doctrine from Phase 2:
│   ├── Extract domains list
│   └── For each domain:
│       ├── ensure_minister_structure(domain_path)
│       ├── For each principle/rule/claim/warning:
│       │   ├── Generate UUID
│       │   ├── Write atomic entry (uuid.json)
│       │   └── Append to doctrine.json
│       └── Update domain-specific vector.index
└── Update combined_vector.index with aggregation metadata
```

## Data Structures

### Atomic Entry File
**Format:** `/ministers/{domain}/{category}/{uuid}.json`

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

### Domain Doctrine Summary
**Format:** `/ministers/{domain}/doctrine.json`

```json
{
  "domain": "constraints",
  "aggregated_from": [
    {"book": "TNA13Crawford2009", "chapter": 1},
    {"book": "TNA13Crawford2009", "chapter": 3}
  ],
  "principles": [
    {"id": "uuid1", "text": "..."},
    {"id": "uuid2", "text": "..."}
  ],
  "rules": [
    {"id": "uuid3", "text": "..."}
  ],
  "claims": [
    {"id": "uuid4", "text": "..."}
  ],
  "warnings": [
    {"id": "uuid5", "text": "..."}
  ],
  "meta": {
    "total_entries": 35,
    "last_updated": "2026-02-11T12:52:27Z"
  }
}
```

### Combined Vector Index
**Format:** `/data/combined_vector.index`

```json
{
  "domain": "all",
  "combined": true,
  "domains_included": [
    "adaptation", "base", "conflict", ..., "truth"
  ],
  "domain_statistics": {
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

## PostgreSQL Vector Database

### Schema Setup

```sql
-- Combined embeddings table (all domains)
CREATE TABLE minister_embeddings (
    id UUID PRIMARY KEY,
    domain VARCHAR(50),
    category VARCHAR(50),  -- principle/rule/claim/warning
    text TEXT,
    embedding VECTOR(1536),
    source_book VARCHAR(255),
    source_chapter INT,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP
);

CREATE INDEX idx_minister_embeddings_vector
    ON minister_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 200);

-- Domain-specific embeddings table
CREATE TABLE minister_domain_embeddings (
    id UUID PRIMARY KEY,
    domain VARCHAR(50),
    category VARCHAR(50),
    text TEXT,
    embedding VECTOR(1536),
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP
);

CREATE INDEX idx_minister_domain_embeddings_vector
    ON minister_domain_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Vector Search Queries

**Search within a domain:**
```sql
SELECT id, category, text, embedding <-> query_vector AS distance
FROM minister_embeddings
WHERE domain = 'constraints'
ORDER BY distance
LIMIT 10;
```

**Cross-domain similarity search:**
```sql
SELECT id, domain, category, text, embedding <-> query_vector AS distance
FROM minister_embeddings
ORDER BY distance
LIMIT 25;
```

## Integration with Ingestion Pipeline

The Phase 3.5 conversion runs **automatically after Phase 3** in the full ingestion pipeline:

```
Phase 0   → PDF Extraction
Phase 0.5 → Glyph Repair
Phase 1   → Chapter Splitting
Phase 2   → Doctrine Extraction
Phase 2.5 → Minister Memories (stub)
Phase 3   → Embeddings
Phase 3.5 → Minister Conversion  <-- NEW
└─→ Completes ingestion
```

### Progress Tracking

Phase 3.5 outputs to:
- `{storage}/03_5_minister_conversion.json` - Conversion summary
- `{storage}/03_5_minister_errors.log` - Any errors (non-fatal)

Example summary:
```json
{
  "status": "success",
  "total_chapters_processed": 9,
  "total_entries_created": 247,
  "domains_populated": 14,
  "domain_statistics": {
    "adaptation": 23,
    "constraints": 31,
    "psychology": 28,
    ...
  }
}
```

## Usage

### Full Pipeline (Automatic Phase 3.5)
```bash
cd /era/ingestion/v2
python -m src.ingest_pipeline /path/to/pdf.pdf
```

### Manual Conversion (Advanced)
```python
from ingestion.v2.src.minister_converter import convert_all_doctrines
import json

# Load doctrines from Phase 2
with open("rag_storage/book_id/02_doctrine.json") as f:
    doctrines = json.load(f)

# Convert
summary = convert_all_doctrines(
    doctrines,
    book_slug="book_id",
    data_root="data"
)

print(f"Created {summary['total_entries_created']} entries")
```

### Program Against the Structure

**Query a domain's doctrine:**
```python
import json

domain = "constraints"
with open(f"data/ministers/{domain}/doctrine.json") as f:
    doctrine = json.load(f)

# Count principles
principle_count = len(doctrine["principles"])
print(f"{domain} has {principle_count} principles")

# Get all rules
rules = doctrine["rules"]
for rule in rules:
    print(f"- {rule['text']}")
```

**Load an atomic entry:**
```python
import json
from pathlib import Path

# Find all principle IDs in constraints domain
principles_dir = Path("data/ministers/constraints/principles")
for entry_file in principles_dir.glob("*.json"):
    with open(entry_file) as f:
        entry = json.load(f)
    print(f"{entry['id']}: {entry['text'][:60]}...")
```

## Vector Embedding Integration

Once PostgreSQL is set up, fill embeddings:

```python
from minister_vector_db import MinisterVectorDB
from sentence_transformers import SentenceTransformer

db = MinisterVectorDB("postgresql://user:pass@localhost/minister_db")
db.init_schema()

# Load embeddings from Phase 3
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

for domain in os.listdir("data/ministers"):
    for category in ["principles", "rules", "claims", "warnings"]:
        cat_dir = f"data/ministers/{domain}/{category}"
        for entry_file in Path(cat_dir).glob("*.json"):
            with open(entry_file) as f:
                entry = json.load(f)
            
            # Generate embedding
            vec = embedding_model.encode(entry["text"])
            
            # Store in database
            db.insert_combined_embedding(
                domain=domain,
                category=category,
                text=entry["text"],
                embedding=vec,
                source_book=entry["source"]["book"],
                source_chapter=entry["source"]["chapter"]
            )

db.close()
```

## Error Handling

Phase 3.5 is **non-fatal** — if conversion fails:
- Error logged to `03_5_minister_errors.log`
- Ingestion pipeline continues
- Core doctrine and embedding data remain valid
- Manual recovery possible with `convert_all_doctrines()`

## Performance Characteristics

- **Throughput:** ~100-200 entries/sec (typical)
- **Memory:** Minimal (streaming atomic writes)
- **I/O:** Sequential writes to domain folders
- **Scaling:** Linear with total doctrine entries

For a typical 300-page book with 200+ doctrine entries:
- Expected Phase 3.5 time: <5 seconds
- Typical total entries created: 150-400
- Expected domains populated: 8-16 of 18

## Future Enhancements

1. **Parallel domain processing** - Process 18 domains concurrently
2. **Batch vector insertion** - Queue embeddings for bulk DB insert
3. **Incremental updates** - Only process new chapters
4. **Domain confidence scoring** - Weight domain assignments
5. **Cross-domain relationship mapping** - Track principle dependencies
6. **Vector cache** - Pre-compute common query vectors
