# Research Workspace Starter Kit

This workspace operationalizes the plan in `research_paper_execution_plan.md`.

## Included assets
- `data/processed/dataset_master.csv`: chapter-level scoring dataset template.
- `rubric/rubric_v1.csv`: 1–5 scoring rubric with dimension descriptors.
- `notes/chapter_log_template.md`: per-chapter evidence logging template.
- `drafts/outline.md`: paper structure with section prompts.
- `references/source_matrix.csv`: literature review extraction matrix.
- `appendix/README.md`: appendix content checklist.

## Suggested execution order
1. Finalize sample and chapters.
2. Pilot rubric on 2 chapters.
3. Score all chapters in `dataset_master.csv`.
4. Draft findings tables/figures.
5. Write full paper from `drafts/outline.md`.


## Tracking + automation
- `progress/milestone_tracker.csv`: track M1-M6 progress, dates, and evidence links.
- `tools/analyze_dataset.py`: computes overall and subject-wise averages from scored dataset.
- `reports/README.md`: report generation instructions.

Run report generation:
```bash
python research/tools/analyze_dataset.py \
  --input research/data/processed/dataset_master.csv \
  --output research/reports/summary.md
```

Validate dataset integrity before analysis:
```bash
python research/tools/validate_dataset.py \
  --input research/data/processed/dataset_master.csv
```

## Validate tooling
```bash
python -m unittest -v tests/test_analyze_dataset.py tests/test_validate_dataset.py
```
