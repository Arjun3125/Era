"""
Doctrine Loader - Reads and parses YAML doctrine files for ministers and Prime Confident.

Each doctrine file may contain:
- role_type: "minister" or "confidant"
- persona.canon: Core worldview and mental models
- doctrine: Purpose, authority, triggers, failure modes, and scope
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class DoctrinalCanon:
    name: str
    role_type: str
    canon_text: str
    purpose: str
    authority_may: List[str]
    authority_may_not: List[str]
    scope: str
    prohibitions: List[str]
    triggers_speak: List[str]
    triggers_silent: List[str]
    failure_modes: List[str]
    correction_mechanisms: List[str]
    raw: Dict[str, Any]


class DoctrineLoader:
    """Utility loader and parsers for doctrine YAML files."""

    @staticmethod
    def load(identifier: str, base_dir: Optional[str] = None) -> Optional[DoctrinalCanon]:
        """
        Load a doctrine YAML by identifier or file path.
        Returns None if the doctrine cannot be loaded.
        """
        path = DoctrineLoader._resolve_path(identifier, base_dir)
        if not path or not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return None

        persona = data.get("persona", {}) or {}
        doctrine = data.get("doctrine", {}) or {}
        authority = doctrine.get("authority", {}) or {}
        triggers = doctrine.get("triggers", {}) or {}

        canon_text = str(persona.get("canon", "") or "")

        return DoctrinalCanon(
            name=str(data.get("name", identifier)),
            role_type=str(data.get("role_type", "")),
            canon_text=canon_text,
            purpose=str(doctrine.get("purpose", "") or ""),
            authority_may=list(authority.get("may", []) or []),
            authority_may_not=list(authority.get("may_not", []) or []),
            scope=str(doctrine.get("scope", "") or doctrine.get("owns", "") or ""),
            prohibitions=list(doctrine.get("prohibitions", []) or []),
            triggers_speak=list(triggers.get("speak", []) or []),
            triggers_silent=list(triggers.get("silent", []) or []),
            failure_modes=list(doctrine.get("failure_modes", []) or []),
            correction_mechanisms=list(doctrine.get("correction_mechanisms", []) or []),
            raw=data,
        )

    @staticmethod
    def extract_worldview_keywords(canon_text: str) -> List[str]:
        """Extract worldview bullet points from the canon text."""
        section = DoctrineLoader._extract_section(canon_text, "Core Worldview")
        return DoctrineLoader._extract_bullets(section)

    @staticmethod
    def extract_warnings(canon_text: str) -> List[str]:
        """Extract typical warning bullet points from the canon text."""
        section = DoctrineLoader._extract_section(canon_text, "Typical Warnings")
        return DoctrineLoader._extract_bullets(section)

    @staticmethod
    def should_speak_based_on_doctrine(
        doctrine: DoctrinalCanon,
        *,
        signals: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ) -> bool:
        """
        Decide if the doctrine suggests speaking based on simple trigger matching.
        This is intentionally conservative and returns True if unsure.
        """
        if doctrine is None:
            return True

        speak_triggers = [t.lower() for t in doctrine.triggers_speak]
        silent_triggers = [t.lower() for t in doctrine.triggers_silent]

        haystack = " ".join(filter(None, [context, " ".join((signals or {}).get("tags", []))])).lower()

        if speak_triggers and any(t in haystack for t in speak_triggers):
            return True
        if silent_triggers and any(t in haystack for t in silent_triggers):
            return False

        return True

    @staticmethod
    def _resolve_path(identifier: str, base_dir: Optional[str]) -> Optional[str]:
        if os.path.exists(identifier):
            return identifier

        name = identifier
        if not name.endswith(".yaml") and not name.endswith(".yml"):
            name = f"{name}.yaml"

        if base_dir is None:
            base_dir = os.environ.get("ERA_DOCTRINE_DIR")

        if base_dir is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(repo_root, "data", "doctrine", "locked")

        return os.path.join(base_dir, name)

    @staticmethod
    def _extract_section(text: str, title: str) -> str:
        if not text:
            return ""
        lines = text.splitlines()
        capture = False
        collected: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if capture:
                    # stop on blank line after capture begins
                    break
                continue
            if stripped.lower().startswith(title.lower()):
                capture = True
                continue
            if capture:
                # stop if a new heading-like line appears
                if stripped.endswith(":") or stripped.isupper():
                    break
                collected.append(stripped)
        return "\n".join(collected)

    @staticmethod
    def _extract_bullets(section: str) -> List[str]:
        bullets: List[str] = []
        if not section:
            return bullets
        for line in section.splitlines():
            item = line.strip().lstrip("-").lstrip("•").lstrip("–").strip()
            if item:
                bullets.append(item)
        return bullets
