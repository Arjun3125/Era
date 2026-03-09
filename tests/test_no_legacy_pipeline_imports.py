"""Guardrails to prevent new pipeline modules from reintroducing legacy imports."""

from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_TARGETS = (
    Path("run_refactored.py"),
    Path("system_main.py"),
    Path("modules/domain_analysis/engine.py"),
    Path("modules/knowledge_synthesis/engine.py"),
    Path("modules/council_execution/engine.py"),
    Path("modules/prime_decision/engine.py"),
)
_FORBIDDEN_SNIPPETS = (
    "from persona.",
    "import persona.",
    "from sovereign.",
    "import sovereign.",
    'import_module("persona',
)


def test_refactored_entrypoints_and_pipeline_engines_do_not_import_legacy_persona_or_sovereign():
    violations: list[str] = []
    for rel_path in _TARGETS:
        content = (_ROOT / rel_path).read_text(encoding="utf-8")
        for snippet in _FORBIDDEN_SNIPPETS:
            if snippet in content:
                violations.append(f"{rel_path.as_posix()}: contains '{snippet}'")
    assert violations == []
