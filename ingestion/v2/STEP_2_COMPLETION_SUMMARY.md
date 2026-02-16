"""
STEP 2: INGESTION PIPELINE INTEGRATION - COMPLETION SUMMARY

OBJECTIVE:
Create hooks between the async ingestion pipeline and ML wisdom system
so that doctrine ingestion feeds learning outcomes to the ML model.

DELIVERABLES:
"""

## 📋 DELIVERABLES COMPLETED

### 1. **ingestion_kis_enhancer.py** (330+ lines)
**Location:** `c:\era\ingestion\v2\src\ingestion_kis_enhancer.py`

**Purpose:** Core integration class between ingestion pipeline and KIS system.

**Key Classes:**
- `IngestionKISContext`: Captures doctrine processing metadata
- `IngestionKISEnhancer`: Main bridge class (6 core methods)

**Methods:**
1. `enhance_aggregation_stage()` - Synthesize KIS for doctrine chunk
2. `enhance_minister_doctrine()` - Add KIS guidance to minister JSON
3. `record_ingestion_success()` - Log successful doctrine ingestion
4. `record_ingestion_failure()` - Log failed ingestion for learning
5. `get_ingestion_statistics()` - Track enhancement metrics
6. `save_ingestion_logs()` - Export logs to JSON

**Technical Details:**
- Creates KISRequest for each doctrine chapter
- Queries related guidance from KIS knowledge base
- Enhances minister JSON with kis_guidance + kis_context fields
- Records outcomes in ML orchestrator for training
- Tracks enhancement rate and knowledge synthesis metrics

**Self-Contained Test:**
```python
# Run test at bottom of file:
enhancer = IngestionKISEnhancer()
context = IngestionKISContext(
    chapter_title="Risk Management",
    minister_domain="career_risk",
    doctrine_excerpt="Financial buffers...",
    ingestion_job_id="ingest_001"
)
context = enhancer.enhance_aggregation_stage(context)
# Output: Enhanced with N related knowledge items
```

---

### 2. **INTEGRATION_GUIDE_KIS.md** (200+ lines)
**Location:** `c:\era\ingestion\v2\INTEGRATION_GUIDE_KIS.md`

**Purpose:** Complete step-by-step integration guide for the ingestion pipeline.

**Contents:**
- 6 modification steps with code locations
- How to wire KIS into AsyncIngestionOrchestrator
- Decision → Outcome feedback loop explanation
- Expected data flow diagram
- Integration checklist

**Key Sections:**
1. **STEP 1: ADD IMPORTS** - What to import where
2. **STEP 2: INITIALIZE KIS ENHANCER** - In orchestrator __init__
3. **STEP 3: ENHANCE AGGREGATION STAGE** - Query KIS for doctrines
4. **STEP 4: TRACK SUCCESS IN STORAGE WRITER** - Record outcomes
5. **STEP 5: EXPORT INGESTION LOGS** - Persist learning data
6. **STEP 6: DECISION → OUTCOME FEEDBACK LOOP** - How ML learns

---

### 3. **CONCRETE_MODIFICATIONS_EXAMPLE.md** (200+ lines)
**Location:** `c:\era\ingestion\v2\CONCRETE_MODIFICATIONS_EXAMPLE.md`

**Purpose:** Exact before/after code examples showing what to change.

**Contains:**
- 5 specific code modifications with line numbers
- All changes marked with `### KIS INTEGRATION ###` tags
- Before/after comparisons
- Summary table of lines/changes per modification
- Backward compatibility notes
- Validation instructions

**Modifications:**
1. Add imports (5 lines) - Optional KIS import with fallback
2. Initialize enhancer (8 lines) - Create kis_enhancer instance
3. Enhance doctrines (30 lines) - Loop through chapters, synthesize knowledge
4. Record success (10 lines) - Log ingestion outcomes for training
5. Handle errors (5 lines) - Record failures on exception

**Total:** ~58 lines of new code spread across ingest_pipeline.py

---

## 🔗 DATA FLOW AFTER INTEGRATION

```
User Input (Books/Doctrine)
    ↓
PHASE 1: CHUNKING
    ↓
PHASE 2: EXTRACTION
    ├─ Extract doctrine from chapters
    ├─ Enrich with metadata
    └─ Write to 02_doctrine.json
    ↓
PHASE 2.5: BUILD MINISTER MEMORIES
    ├─ [existing logic]
    └─ [now with KIS context]
    ↓
PHASE 3: EMBEDDINGS & KIS SYNTHESIS
    ├─ For each doctrine chapter:
    │  ├─ Create IngestionKISContext
    │  ├─ Query: "What KIS guidance for this domain?"
    │  ├─ Enhance doctrine with kis_guidance[]
    │  ├─ Embed with enhanced context
    │  └─ Track job outcome
    ↓
PHASE 4: STORAGE
    ├─ Write embeddings to pgvector
    └─ Record ingestion success
    │  └─ kis_enhancer.record_ingestion_success()
    │     └─ ML system learns pattern
    ↓
ML WISDOM SYSTEM
    ├─ Groups: (doctrine_type, domain, book_source)
    ├─ Learns: Did KIS guidance help ingestion?
    ├─ Adjusts: KIS weights for next ingestion
    └─ Exports: ml/cache/ingestion_kis_logs.json
```

---

## 📊 LEARNING FLOW

```
DOCTRINE INGESTION:
Step 1: KIS Synthesis
  - Query: "Career risk doctrine guidance?"
  - Return: [5 related knowledge items with scores]

Step 2: Enhance Document
  - Add kis_guidance[] to doctrine JSON
  - Add kis_context{} with trace/quality

Step 3: Process & Store
  - Embed with KIS context
  - Write to pgvector
  - Record: "ingestion succeeded"

Step 4: ML Training
  - Situation: (career_risk, Babylon book, Chapter 5)
  - Outcome: Success
  - Learn: KIS guidance effective for this type
  - Adjust KIS prior weights ↑

Next Ingestion:
  - KIS makes slightly different choices
  - System improves from experience
```

---

## 🎯 INTEGRATION POINTS

### Where Changes Go:
1. **ingestion/v2/src/ingest_pipeline.py**
   - Add imports (line ~18)
   - Initialize kis_enhancer (line ~560 in run_full_ingest_with_resume)
   - Enhance doctrines (line ~425 before _enrich_doctrines)
   - Record success (line ~530 after embeddings written)
   - Handle errors (in exception handlers)

2. **ingestion/v2/src/ingestion_kis_enhancer.py**
   - NEW FILE - No changes to existing code

3. **ml/kis/knowledge_integration_system.py**
   - Already exists - No changes needed

4. **ml/ml_orchestrator.py**
   - Already exists - No changes needed

---

## ✅ VERIFICATION CHECKLIST

### Self-Test of IngestionKISEnhancer:
- [x] Import IngestionKISEnhancer from ingestion_kis_enhancer.py
- [x] Initialize with default knowledge base path
- [x] Create IngestionKISContext
- [x] Call enhance_aggregation_stage()
- [x] Verify kis_synthesis is populated
- [x] Record success/failure
- [x] Export logs to JSON

### Integration Test (after modifications):
- [ ] Modify ingest_pipeline.py (add 5 modifications)
- [ ] Run ingestion: `python ingestion/v2/run_all_v2_ingest.py`
- [ ] Check output: "[KIS] messages should appear"
- [ ] Verify: ml/cache/ingestion_kis_logs.json created
- [ ] Inspect: kis_guidance fields in resulting doctrines

---

## 📈 EXPECTED METRICS

After integration, you should see:

```
KIS Enhancement Statistics:
- Total Ingestions: [N] books/chapters processed
- Enhanced with KIS: [N] with KIS synthesis
- Enhancement Rate: [%] of ingestions enhanced
- Total Knowledge Synthesized: [N] KIS items queried
- Avg Items per Ingestion: [X] related items per chapter
```

---

## 🚀 NEXT STEPS AFTER VERIFICATION

1. **Apply modifications** to ingest_pipeline.py (5 concrete changes)
2. **Test integration** by running a small ingestion job
3. **Verify output** - check ingestion_kis_logs.json
4. **Validate learning** - run ML training on outcomes
5. **Measure impact** - compare ingestion metrics before/after

---

## 📝 FILES CREATED IN STEP 2

```
c:\era\ingestion\v2\
├── src\
│   └── ingestion_kis_enhancer.py ..................... (330 lines) ✅
├── INTEGRATION_GUIDE_KIS.md .......................... (200 lines) ✅
└── CONCRETE_MODIFICATIONS_EXAMPLE.md ................ (200 lines) ✅

Supporting Files (Not Modified):
- c:\era\ml\kis\knowledge_integration_system.py ....... (250 lines) ✓
- c:\era\ml\ml_orchestrator.py ........................ (280 lines) ✓
```

---

## 🔄 HOW INGESTION ENABLES ML LEARNING

Traditional Pipeline:
```
Book → Extract Doctrine → Embed → Store → Done
(No learning feedback)
```

With KIS Integration:
```
Book
  ↓
Extract Doctrine
  ├─ With KIS synthesis
  ├─ Enhanced with guidance
  └─ Tracked for learning
  ↓
Embed & Store
  ├─ Record success/failure
  ├─ ML learns pattern
  └─ Adjust KIS weights
  ↓
Next Book
  ├─ Uses learned KIS weights
  ├─ Makes better decisions
  └─ Cycle repeats
```

---

## 🎓 LEARNING PATTERNS

**Pattern 1: Successful Ingestion**
- Situation: Doctrine chapter on career risk + KIS synthesis
- Outcome: Storage succeeded with N embeddings
- Learning: This domain + guidance effective → ↑ weight

**Pattern 2: Failed Ingestion**
- Situation: Unstructured text + KIS synthesis attempted
- Outcome: Embedding failed, storage failed
- Learning: This source type problematic → ↓ weight

**Pattern 3: High-Confidence Guidance**
- Situation: Ministry doctrine matches known pattern
- Outcome: KIS guidance + ingestion both successful
- Learning: Pattern is reliable → ↑ confidence gate

---

## 🔗 CONNECTION TO EARLIER STEPS

**Step 1: Minister KIS Bridge** ✅
- Ministers query KIS for guidance
- Decisions recorded with confidence
- Outcomes feed ML training

**Step 2: Ingestion Pipeline Integration** ✅ (JUST COMPLETED)
- Doctrines query KIS during aggregation
- Ingestion outcomes feed ML training
- Pipeline learns which guidance helps ingest

**Step 3: LLM Client** (NEXT)
- Implement actual LLM calls (now just mocked)
- Wire to Ollama/Claude API
- Get real-time LLM reasoning

**Step 4: Training Data Collection** (NEXT)
- Batch outcomes from Steps 1 & 2
- Train ML weights on collected data
- Persist learned weights

**Step 5: End-to-End Testing** (NEXT)
- Run full pipeline: Minister → KIS → Ingestion → ML
- Verify learning feedback loops work
- Check performance improvements

**Step 6: Deployment** (NEXT)
- Monitor decision quality
- Track learning progress
- Scale to full system

---

## 📚 DOCUMENTATION FILES

**Integration Guide:** `ingestion/v2/INTEGRATION_GUIDE_KIS.md`
- Complete step-by-step modifications
- All 6 integration points explained
- Learning flow documented

**Concrete Examples:** `ingestion/v2/CONCRETE_MODIFICATIONS_EXAMPLE.md`
- Exact line numbers and code
- Before/after comparisons
- Validation instructions

**Code:** `ingestion/v2/src/ingestion_kis_enhancer.py`
- Self-contained, importable
- Fully documented
- Includes test at bottom

---

## ✨ SUMMARY

**STEP 2 COMPLETE: Ingestion Pipeline KIS Integration**

Created comprehensive integration layer (`ingestion_kis_enhancer.py`) with:
- Knowledge synthesis during aggregation phase
- Outcome tracking for ML training
- Full documentation and modification guides
- Backward-compatible (KIS optional)
- Ready for application to ingest_pipeline.py

**Three deliverables:**
1. ✅ `ingestion_kis_enhancer.py` - Integration class (330 lines)
2. ✅ `INTEGRATION_GUIDE_KIS.md` - Step-by-step guide (200 lines)
3. ✅ `CONCRETE_MODIFICATIONS_EXAMPLE.md` - Exact code changes (200 lines)

**Expected impact:**
- Ingestion pipeline provides learning data to ML system
- ML learns which KIS guidance improves ingestion
- Next ingestion uses learned weightings
- Doctrine storage benefits from intelligent KIS synthesis
