"""Simulation phase for continuous training loop."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SimulationConfig:
    scenarios_root: Path
    num_scenarios: int
    seed: int
    alignment_weight: float
    output_path: Path
    category_weights: Optional[Path] = None


def run_simulation(config: SimulationConfig) -> Path:
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        python,
        str(root / "scripts" / "generate_simulated_data.py"),
        "--scenarios-root",
        str(config.scenarios_root),
        "--num-scenarios",
        str(config.num_scenarios),
        "--seed",
        str(config.seed),
        "--output",
        str(output_path),
        "--alignment-weight",
        str(config.alignment_weight),
    ]
    if config.category_weights:
        cmd.extend(["--category-weights", str(config.category_weights)])

    subprocess.run(cmd, check=True)
    return output_path
