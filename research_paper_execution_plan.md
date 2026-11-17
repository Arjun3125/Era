# Research Paper Master Plan (Execution-First)

> **Goal:** Produce a submission-ready, evidence-based research paper on **CBSE Class 10 textbooks** with clear milestones, measurable outputs, and quality checks.

---

## 1) What We Are Making

### Working Title
**A Comparative Analysis of CBSE Class 10 Textbooks: Curriculum Alignment, Readability, and Assessment Readiness**

### Final Outputs (must-have)
1. `paper_draft_v1.docx` (full first draft)
2. `paper_final.docx` + `paper_final.pdf`
3. `dataset_master.csv` (chapter-wise scored data)
4. `rubric_v1.csv` (evaluation criteria and scale definitions)
5. `figures/` (charts used in the paper)
6. `references.bib` or Zotero export
7. `appendix/` (coding notes, rubric description, sampling details)

### Stretch Outputs (nice-to-have)
- 8–12 slide summary deck
- One-page policy brief for teachers/schools

---

## 2) Exact Scope (Lock This Early)

### Subjects to include
- English
- Science
- Mathematics
- Social Science

### Sampling Strategy (recommended)
- **Option A (full):** all chapters from all selected subjects.
- **Option B (time-limited):** 5 representative chapters per subject:
  - 2 easy/foundational
  - 2 medium
  - 1 high-complexity chapter

### Research Questions
1. How closely do textbook chapters align with stated CBSE learning outcomes?
2. Are concepts sequenced and explained in a learner-friendly way?
3. How effectively do textbook exercises prepare students for board-style competency-based assessment?
4. Which subject(s) perform best/worst across objective quality dimensions?

---

## 3) Folder + File Setup (Do This First)

Create this structure:

```text
research/
  data/
    raw/
    processed/
  rubric/
  notes/
  drafts/
  figures/
  appendix/
  references/
```

Create starter files:
- `data/processed/dataset_master.csv`
- `rubric/rubric_v1.csv`
- `notes/chapter_log_template.md`
- `drafts/outline.md`
- `references/source_matrix.csv`

---

## 4) What to Include in the Paper (Section Blueprint)

## A. Abstract (200-300 words)
- Context
- Method
- 3-4 key findings
- 1-line implication

## B. Introduction
- Why Class 10 textbooks matter (exam and foundational stage)
- Problem statement (quality varies; limited structured comparison)
- Objectives + research questions

## C. Literature Review
- Textbook quality frameworks
- Readability and school learning
- Competency-based assessment alignment
- Gap in existing studies

## D. Methodology
- Design: mixed-method content analysis
- Sample details (subjects/chapters/edition/year)
- Rubric dimensions + scoring (1-5)
- Reliability process (pilot + recheck)
- Data analysis plan (descriptive stats + thematic notes)

## E. Findings
- Subject-wise score tables
- Dimension-wise comparison (alignment/readability/assessment)
- Top 5 strengths
- Top 5 critical gaps

## F. Discussion
- Why patterns occurred
- How findings compare with prior studies
- Implications for teachers/students/curriculum planners

## G. Recommendations
- Quick fixes (next edition)
- Medium-term improvements
- Assessment-support improvements

## H. Conclusion + Limitations + Future Work

## I. References + Appendix

---

## 5) Evaluation Rubric (What to Perform on Each Chapter)

Score each dimension from **1 (poor) to 5 (excellent)**:

1. **Curriculum Alignment**
2. **Concept Sequencing/Scaffolding**
3. **Language Readability**
4. **Worked Examples Quality**
5. **Practice Exercise Diversity**
6. **Competency/HOTS Support**
7. **Inclusivity & Contextual Relevance**
8. **Visual/Pedagogic Design Quality**

### Minimum data row fields per chapter
- Subject
- Book/edition/year
- Chapter name
- Chapter pages
- Score (8 dimensions)
- Mean score
- Key strengths (2-3 bullets)
- Key gaps (2-3 bullets)
- Evidence note (page references)

---

## 6) 21-Day Execution Timeline (Milestones + Paths)

## Milestone Path M1 -> M6

### **M1: Planning Locked (Day 1-2)**
**Tasks**
- Finalize topic, research questions, and sample strategy
- Build folder structure and templates
- Start bibliography manager

**Exit Criteria**
- Scope finalized in writing
- All starter files created

---

### **M2: Rubric Validated (Day 3-4)**
**Tasks**
- Draft rubric descriptors for score 1 to 5
- Pilot on 1 chapter per subject
- Refine ambiguous criteria

**Exit Criteria**
- `rubric_v1.csv` frozen
- Pilot notes completed

---

### **M3: Data Collection Complete (Day 5-11)**
**Tasks**
- Score all selected chapters
- Fill dataset row-by-row
- Capture evidence notes with page references

**Exit Criteria**
- 100% chapter coverage
- No missing score fields

---

### **M4: Analysis Complete (Day 12-14)**
**Tasks**
- Compute descriptive statistics
- Build visuals (bar/heatmap/radar)
- Identify top strengths + major gaps

**Exit Criteria**
- At least 4 figures and 3 tables ready
- Findings summary note completed

---

### **M5: Draft Complete (Day 15-18)**
**Tasks**
- Write Methodology and Findings first
- Then Introduction, Discussion, Conclusion
- Insert references and captioned figures

**Exit Criteria**
- Full draft (all sections present)
- Citation placeholders resolved

---

### **M6: Submission Ready (Day 19-21)**
**Tasks**
- Language polish and formatting cleanup
- Similarity/plagiarism check
- Final compliance review (style guide)

**Exit Criteria**
- `paper_final.docx` and `paper_final.pdf` exported
- Submission package archived

---

## 7) Weekly Progress Tracker

### Week 1 (Days 1-7)
- Scope lock
- Rubric pilot + freeze
- Begin chapter coding

### Week 2 (Days 8-14)
- Finish coding
- Build figures/tables
- Finalize findings summary

### Week 3 (Days 15-21)
- Write full draft
- Revise
- Finalize and submit

---

## 8) Quality Control Checklist (Non-Negotiable)

- [ ] Rubric has explicit descriptors for each score level
- [ ] At least one pilot chapter per subject completed
- [ ] Evidence notes include page-level references
- [ ] All figures have titles and interpretation text
- [ ] Every major claim links to data table/figure/source
- [ ] Reference style is consistent (APA/MLA/IEEE)
- [ ] Final version passed grammar + formatting review

---

## 9) How to Enhance Quality Further (Best Suggestions)

1. Add a second reviewer for 10-20% of chapters to improve reliability.
2. Build a literature matrix (author, method, finding, limitation) before writing review.
3. Add one short teacher/student feedback component (if feasible).
4. Report both averages and dispersion (not only mean scores).
5. Include at least one negative case where a chapter underperforms despite good design.
6. Keep a decision log for methodological changes.
7. Write the discussion around implications, not only description.

---

## 10) Risk Register + Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Scope too broad | High | High | Use fixed chapter sample strategy before coding |
| Inconsistent scoring | Medium | High | Pilot + descriptor refinement + recheck |
| Weak literature review | Medium | Medium | Minimum target: 20 quality sources |
| Draft delays | High | High | Write sections in parallel with analysis |
| Citation errors | Medium | Medium | Use reference manager from Day 1 |

---

## 11) Minimum Acceptance Criteria (Definition of Done)

Your work is complete only when:
1. All selected chapters are scored and evidenced.
2. At least 4 figures + 3 tables are integrated into the paper.
3. All paper sections are fully written.
4. References are complete and consistently formatted.
5. Final document is exported and ready for submission.

---

## 11A) Execution Automation (Recommended)

Use the included analysis helper to convert scored CSV data into a shareable markdown report:

```bash
python research/tools/analyze_dataset.py \
  --input research/data/processed/dataset_master.csv \
  --output research/reports/summary.md
```

Validate dataset quality before generating reports:

```bash
python research/tools/validate_dataset.py \
  --input research/data/processed/dataset_master.csv
```

Track milestone completion in:
- `research/progress/milestone_tracker.csv`

---

## 12) Quick Start (Today)

If starting now, do these 5 actions immediately:
1. Create the folder structure and starter files.
2. Finalize sample strategy (full vs representative chapters).
3. Draft rubric dimensions and score descriptors.
4. Pilot 2 chapters and refine rubric.
5. Start master dataset with the first 10 rows.

That gives you a strong launch and prevents rework later.
