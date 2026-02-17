"""
Council package exports.

This package coexists with the legacy ``persona/council.py`` module. Because the
package shadows that module name, we explicitly load the legacy module and
re-export its public classes here for backwards compatibility.
"""

import importlib.util
import sys
from pathlib import Path


def _load_legacy_council():
    legacy_path = Path(__file__).resolve().parent.parent / "council.py"
    spec = importlib.util.spec_from_file_location("persona._council_legacy", legacy_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to create import spec for legacy council module")

    module = importlib.util.module_from_spec(spec)
    sys.modules["persona._council_legacy"] = module
    spec.loader.exec_module(module)
    return module


_legacy = _load_legacy_council()
CouncilAggregator = _legacy.CouncilAggregator
CouncilRecommendation = _legacy.CouncilRecommendation

from .dynamic_council import DynamicCouncil

__all__ = [
    "CouncilAggregator",
    "CouncilRecommendation",
    "DynamicCouncil",
]
