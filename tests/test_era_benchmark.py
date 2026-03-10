from pathlib import Path
import json


def test_benchmark_index_counts_match_files():
    root = Path("era_benchmark")
    index = json.loads((root / "benchmark_index.json").read_text(encoding="utf-8"))
    expected_total = index["scenario_count"]
    total_files = 0
    for cat, count in index["categories"].items():
        files = list((root / "scenarios" / cat).glob("*.json"))
        assert len(files) == count, f"{cat} count mismatch"
        total_files += len(files)
    assert total_files == expected_total
