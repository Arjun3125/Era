import csv
import tempfile
import unittest
from pathlib import Path
import importlib.util


MODULE_PATH = Path("research/tools/analyze_dataset.py")
spec = importlib.util.spec_from_file_location("analyze_dataset", MODULE_PATH)
analyze_dataset = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(analyze_dataset)


class AnalyzeDatasetTests(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(analyze_dataset.to_float("3"), 3.0)
        self.assertEqual(analyze_dataset.to_float(" 4.5 "), 4.5)
        self.assertIsNone(analyze_dataset.to_float(""))
        self.assertIsNone(analyze_dataset.to_float("n/a"))

    def test_load_rows_missing_columns_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.csv"
            path.write_text("subject,chapter_title\nScience,Atoms\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                analyze_dataset.load_rows(path)

    def test_summarize_and_render(self):
        rows = [
            {
                "subject": "Science",
                "curriculum_alignment": "4",
                "sequencing_scaffolding": "3",
                "language_readability": "5",
                "worked_examples": "4",
                "exercise_diversity": "4",
                "competency_hots": "3",
                "inclusivity_context": "4",
                "visual_design": "4",
            },
            {
                "subject": "Science",
                "curriculum_alignment": "2",
                "sequencing_scaffolding": "3",
                "language_readability": "3",
                "worked_examples": "2",
                "exercise_diversity": "3",
                "competency_hots": "2",
                "inclusivity_context": "3",
                "visual_design": "3",
            },
            {
                "subject": "Mathematics",
                "curriculum_alignment": "5",
                "sequencing_scaffolding": "4",
                "language_readability": "4",
                "worked_examples": "5",
                "exercise_diversity": "4",
                "competency_hots": "5",
                "inclusivity_context": "4",
                "visual_design": "4",
            },
        ]

        overall, by_subject, valid_rows = analyze_dataset.summarize(rows)
        self.assertEqual(valid_rows, 3)
        self.assertAlmostEqual(overall["curriculum_alignment"], 3.667, places=3)
        self.assertAlmostEqual(by_subject["Science"]["worked_examples"], 3.0, places=3)
        self.assertAlmostEqual(by_subject["Mathematics"]["competency_hots"], 5.0, places=3)

        report = analyze_dataset.render_markdown(overall, by_subject, valid_rows)
        self.assertIn("# Dataset Summary Report", report)
        self.assertIn("Scored rows detected: **3**", report)
        self.assertIn("### Science", report)

    def test_end_to_end_cli_helpers(self):
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
        ]
        row = {
            "subject": "English",
            "curriculum_alignment": "4",
            "sequencing_scaffolding": "4",
            "language_readability": "5",
            "worked_examples": "3",
            "exercise_diversity": "4",
            "competency_hots": "3",
            "inclusivity_context": "4",
            "visual_design": "4",
        }

        with tempfile.TemporaryDirectory() as td:
            in_path = Path(td) / "input.csv"
            out_path = Path(td) / "output.md"
            with in_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerow(row)

            rows = analyze_dataset.load_rows(in_path)
            overall, by_subject, valid_rows = analyze_dataset.summarize(rows)
            report = analyze_dataset.render_markdown(overall, by_subject, valid_rows)
            out_path.write_text(report, encoding="utf-8")

            text = out_path.read_text(encoding="utf-8")
            self.assertIn("### English", text)
            self.assertIn("| curriculum_alignment | 4.0 |", text)


if __name__ == "__main__":
    unittest.main()
