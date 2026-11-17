import csv
import tempfile
import unittest
from pathlib import Path
import importlib.util


MODULE_PATH = Path("research/tools/validate_dataset.py")
spec = importlib.util.spec_from_file_location("validate_dataset", MODULE_PATH)
validate_dataset = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validate_dataset)


class ValidateDatasetTests(unittest.TestCase):
    def write_csv(self, path: Path, rows):
        headers = [
            "subject",
            "curriculum_alignment",
            "sequencing_scaffolding",
            "language_readability",
            "worked_examples",
            "exercise_diversity",
            "competency_hots",
            "inclusivity_context",
            "visual_design",
            "mean_score",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def test_valid_dataset_passes(self):
        row = {
            "subject": "Science",
            "curriculum_alignment": "4",
            "sequencing_scaffolding": "4",
            "language_readability": "4",
            "worked_examples": "4",
            "exercise_diversity": "4",
            "competency_hots": "4",
            "inclusivity_context": "4",
            "visual_design": "4",
            "mean_score": "4",
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ok.csv"
            self.write_csv(path, [row])
            ok, errors = validate_dataset.validate_file(path)
            self.assertTrue(ok)
            self.assertEqual(errors, [])

    def test_out_of_range_fails(self):
        row = {
            "subject": "Math",
            "curriculum_alignment": "6",
            "sequencing_scaffolding": "4",
            "language_readability": "4",
            "worked_examples": "4",
            "exercise_diversity": "4",
            "competency_hots": "4",
            "inclusivity_context": "4",
            "visual_design": "4",
            "mean_score": "4",
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.csv"
            self.write_csv(path, [row])
            ok, errors = validate_dataset.validate_file(path)
            self.assertFalse(ok)
            self.assertTrue(any("out of range" in e for e in errors))

    def test_mean_mismatch_fails(self):
        row = {
            "subject": "English",
            "curriculum_alignment": "5",
            "sequencing_scaffolding": "5",
            "language_readability": "5",
            "worked_examples": "5",
            "exercise_diversity": "5",
            "competency_hots": "5",
            "inclusivity_context": "5",
            "visual_design": "5",
            "mean_score": "3.0",
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "mismatch.csv"
            self.write_csv(path, [row])
            ok, errors = validate_dataset.validate_file(path)
            self.assertFalse(ok)
            self.assertTrue(any("differs from computed" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
