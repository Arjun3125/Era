"""Generate checksums for ERA-Bench artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def collect_files(root: Path) -> List[Path]:
    files: List[Path] = []
    files.append(root / "benchmark_index.json")
    files.append(root / "schema.md")
    for path in sorted((root / "scenarios").rglob("*.json")):
        files.append(path)
    splits = root / "splits"
    if splits.exists():
        for path in sorted(splits.rglob("*.json")):
            files.append(path)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ERA-Bench checksums.")
    parser.add_argument("--root", default="era_benchmark")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output) if args.output else root / "checksums.json"

    payload: Dict[str, str] = {}
    for path in collect_files(root):
        rel = path.relative_to(root).as_posix()
        payload[rel] = sha256(path)

    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} checksums to {output}")


if __name__ == "__main__":
    main()
