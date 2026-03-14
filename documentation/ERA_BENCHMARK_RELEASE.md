# ERA-Bench Release Checklist

## 1. Freeze Dataset Version

- Update `era_benchmark/benchmark_index.json` version.
- Regenerate and freeze splits under `era_benchmark/splits/vX_Y/`.
- Commit the dataset and split metadata.

## 2. Create Integrity Artifacts

- Generate checksums for all scenario files and split files.
- Store checksums in `era_benchmark/checksums.json`.

## 3. Choose License

Decide on dataset license and update:
- `documentation/ERA_BENCHMARK_CARD.md`
- `README.md`
- repository LICENSE file if required

## 4. Publish Documentation

- `documentation/ERA_PAPER_DRAFT.md` (paper draft)
- `documentation/ERA_BENCHMARK_CARD.md` (dataset card)
- `documentation/REPOSITORY_TECHNICAL_GUIDE.md`

## 5. Reproducibility

- Ensure `experiments/run_benchmark.py` captures git commit hash.
- Include `experiments/results/<dataset>/<experiment>/experiment.json`.
- Provide example experiment IDs and seeds.

## 6. Tag Release

- Tag git commit (e.g., `era-bench-v1.2`).
- Add a release note with dataset stats and evaluation baseline.

## 7. Optional: Upload Artifacts

If publishing externally:
- `era_benchmark/` (dataset)
- `experiments/` (evaluation harness)
- `training_loop/` (learning infrastructure)

## 8. Citation

Update `CITATION.cff` with author(s), version, and year.
