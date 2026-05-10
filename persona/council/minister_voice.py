"""MinisterVoice — LLM-per-minister deliberation using doctrine YAML as system prompt."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml as _yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

_DOCTRINE_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "doctrine" / "locked"

_YAML_MAP = {
    "risk": "risk", "risk_resources": "risk", "power": "power",
    "grand_strategist": "grand_strategist", "technology": "technology",
    "timing": "timing", "optionality": "optionality", "data": "data",
    "diplomacy": "diplomacy", "psychology": "psychology",
    "legitimacy": "legitimacy", "conflict": "conflict", "truth": "truth",
    "discipline": "discipline", "intelligence": "intelligence",
    "narrative": "narrative", "sovereign": "n",
    "adaptation": "adaptation", "war_mode": "war_mode",
}

_FALLBACK_PERSONA = (
    "You are a wise minister advising on important decisions. "
    "Analyze the situation and give your honest stance."
)


def _load_minister_persona(minister_name: str) -> str:
    """Return the persona canon string from the minister's doctrine YAML."""
    if not _YAML_OK:
        return _FALLBACK_PERSONA
    yaml_name = _YAML_MAP.get(minister_name)
    if not yaml_name:
        return _FALLBACK_PERSONA
    yaml_path = _DOCTRINE_ROOT / f"{yaml_name}.yaml"
    if not yaml_path.exists():
        return _FALLBACK_PERSONA
    try:
        doc = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        canon = (doc.get("persona") or {}).get("canon") or ""
        return canon.strip() or _FALLBACK_PERSONA
    except Exception:
        return _FALLBACK_PERSONA


_MINISTER_INSTRUCTION = """
You are {minister_name} in a council deliberation.

{persona_canon}

---
Relevant knowledge for this situation:
{knowledge_context}

---
Given the situation below, respond ONLY with valid JSON in this exact format:
{{
  "stance": "support" | "oppose" | "neutral",
  "reasoning": "<1-2 sentences. Cite a specific knowledge entry or your doctrine perspective>",
  "confidence": <0.0 to 1.0>,
  "warning": "<optional red-line concern, or empty string>",
  "knowledge_cited": "<entry numbers you drew on, e.g. '1, 3' — or empty string>"
}}
"""


class MinisterVoice:
    """Wraps one minister's LLM deliberation call."""

    def __init__(self, minister_name: str, llm: Any):
        self.minister_name = minister_name
        self.llm = llm
        self._persona = _load_minister_persona(minister_name)
        self._display_name = minister_name.replace("_", " ").title()

    def deliberate(self, user_input: str, context: Dict[str, Any], knowledge_entries: list = None) -> Dict[str, Any]:
        """Call the LLM as this minister. Injects book-derived knowledge entries into prompt."""
        domain_hint = ", ".join(context.get("domains", [])) or "general"

        if knowledge_entries:
            lines = []
            for i, entry in enumerate(knowledge_entries[:6], 1):
                content = str(entry.get("content") or entry.get("text", ""))[:200].strip()
                source = entry.get("source", {})
                book = source.get("book", "") if isinstance(source, dict) else ""
                category = entry.get("type") or entry.get("category", "principle")
                line = f"{i}. [{category}] {content}"
                if book:
                    line += f"  — {book}"
                lines.append(line)
            knowledge_block = "\n".join(lines)
        else:
            knowledge_block = "(No domain knowledge retrieved — reasoning from doctrine only.)"

        system_prompt = _MINISTER_INSTRUCTION.format(
            minister_name=self._display_name,
            persona_canon=self._persona,
            knowledge_context=knowledge_block,
        )

        prompt = f"Domains: {domain_hint}\n\nSituation: {user_input}"
        if context.get("peer_summary"):
            prompt += f"\n\n---\n{context['peer_summary']}"

        try:
            raw = self.llm.analyze(system_prompt, prompt)
            return self._parse(raw)
        except Exception as e:
            return {
                "stance": "neutral",
                "reasoning": f"[{self.minister_name} unavailable: {e}]",
                "confidence": 0.3,
                "warning": "",
                "knowledge_cited": "",
            }

    def _parse(self, raw: str) -> Dict[str, Any]:
        """Parse JSON from LLM output, with robust fallback."""
        # Try direct JSON parse
        try:
            data = json.loads(raw.strip())
            return self._validate(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting JSON block from markdown fencing or surrounding text
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return self._validate(data)
            except Exception:
                pass

        # Plain-text fallback: infer stance from keywords
        text = raw.lower()
        if any(w in text for w in ["oppose", "risk", "danger", "avoid", "caution"]):
            stance = "oppose"
        elif any(w in text for w in ["support", "proceed", "go ahead", "recommend"]):
            stance = "support"
        else:
            stance = "neutral"

        return {
            "stance": stance,
            "reasoning": raw[:200].strip(),
            "confidence": 0.5,
            "warning": "",
            "knowledge_cited": "",
        }

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
        valid_stances = {"support", "oppose", "neutral"}
        stance = str(data.get("stance", "neutral")).lower()
        if stance not in valid_stances:
            stance = "neutral"
        return {
            "stance": stance,
            "reasoning": str(data.get("reasoning", ""))[:400],
            "confidence": max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
            "warning": str(data.get("warning", "")),
            "knowledge_cited": str(data.get("knowledge_cited", "")),
        }
