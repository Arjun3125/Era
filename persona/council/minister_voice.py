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
    "risk": "risk_resources", "risk_resources": "risk_resources", "power": "power",
    "grand_strategist": "grand_strategist", "technology": "technology",
    "timing": "timing", "optionality": "optionality", "data": "data",
    "diplomacy": "diplomacy", "psychology": "psychology",
    "legitimacy": "legitimacy", "conflict": "conflict", "truth": "truth",
    "discipline": "discipline", "intelligence": "intelligence",
    "narrative": "narrative", "sovereign": "sovereign",
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
        if not canon:
            purpose = doc.get("purpose") or ""
            posture = ", ".join(doc.get("posture", [])) if isinstance(doc.get("posture"), list) else ""
            if purpose:
                canon = f"Purpose: {purpose.strip()}"
                if posture:
                    canon += f"\nPosture: {posture}"
        return canon.strip() or _FALLBACK_PERSONA
    except Exception:
        return _FALLBACK_PERSONA


_MINISTER_INSTRUCTION = """
You are {minister_name} in a royal cabinet deliberation.

Your Persona Canon and Domain Doctrine:
{persona_canon}

---
Past Similar Scenarios (for reference — draw patterns, don't repeat them):
{scenario_context}

---
Background Knowledge References (KIS entries — internalize these, do NOT quote or repeat them):
{knowledge_context}

---
CRITICAL DEBATE COMMANDS:
1. SYNTHESIZE, DO NOT QUOTE: The KIS entries above are background reference material to inform YOUR analysis. You MUST NOT quote, repeat, or rephrase KIS entries verbatim. Instead, APPLY those principles to THIS specific situation using YOUR domain doctrine. Your reasoning and advice must come from YOUR understanding of the situation — the KIS entries merely sharpen your lens. If your reasoning sounds like a KIS entry copied with minor edits, you have failed.
2. GROUND IN SITUATION DETAILS: Every sentence in your reasoning and advice must reference something SPECIFIC from the situation — a person's behavior, a concrete risk, a timeline, a trade-off. Abstract generic statements (e.g. "diversification reduces risk") are forbidden. Show you understood THIS situation, not situations in general.
3. You MUST reason strictly through the unique lens of your Persona Canon and Domain Doctrine! Apply your domain's worldview (strategy, power, diplomacy, psychology, risk, timing) to analyze THIS specific situation.
4. DEBATE & ARGUMENT EVOLUTION: If peer stances or arguments from fellow ministers are provided below, you MUST converse and debate! You must actively EVOLVE your argument and advice by listening to your peers' insights—incorporating their valid trade-offs or constraints into your own analysis—while preserving your exact domain positioning (NO DRIFT from your core doctrine!). Address your colleagues by name (e.g., 'Listening to the Risk Minister's warning on liquidity, I evolve my Strategic growth advice by proposing a phased entry...').
5. UNIFIED ADVICE PLAN CONTRIBUTION: You must formulate one clear, actionable recommendation in the 'advice' field that directly stems from your evolved positioning, to be merged into the Sovereign's unified execution plan.
6. INQUIRY & QUESTION FORMULATION: When discussing your domain points, if you face ambiguity or require missing data to make a definitive ruling, you must formulate necessary clarifying questions in the 'questions' list! Ask specific questions to fellow ministers (e.g. 'To Risk Minister: what is our cash buffer?') or to the User/Sovereign (e.g. 'To Sovereign: what is the target timeline?'). In Round 2/3, if a peer minister asked a question directed to your domain, you MUST answer it in your reasoning or advice!
7. VALIDITY TO DOMAIN & SITUATION: Every point, question, and advice item you produce MUST be strictly valid to your unique Domain Doctrine AND directly tailored to the specific Situation above! Do NOT ask generic, canned, or out-of-domain questions. If a question or advice is not 100% relevant to your domain and this specific situation, do not include it!

Given the situation below, respond ONLY with valid JSON in this exact format:
{{
  "stance": "support" | "oppose" | "neutral",
  "reasoning": "<1-3 sentences. SYNTHESIZE your own analysis grounded in THIS situation's specifics! Reference concrete details from the situation. Do NOT rephrase KIS entries. In Round 2/3, explicitly state how your argument evolved and answer any peer questions!>",
  "advice": "<1 concise, domain-specific actionable recommendation. Must reference something concrete from THIS situation — no generic advice.>",
  "questions": [
    "<Optional question for a fellow minister valid to your domain, e.g. 'To Risk Minister: What is our downside cap?'>",
    "<Optional clarifying question for the User/Sovereign tailored to this exact situation>"
  ],
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

    def deliberate(self, user_input: str, context: Dict[str, Any], knowledge_entries: list = None, scenario_context: str = "") -> Dict[str, Any]:
        """Call the LLM as this minister. Injects book-derived knowledge entries into prompt."""
        domain_hint = ", ".join(context.get("domains", [])) or "general"

        if knowledge_entries:
            grouped = {}
            for idx, e in enumerate(knowledge_entries, 1):
                cat = e.get("type", "principle").upper()
                if not cat.endswith("S"):
                    cat += "S"
                if cat not in grouped:
                    grouped[cat] = []
                grouped[cat].append(f"  [{idx}] {e.get('content', '')}")
            lines = []
            for cat, items in grouped.items():
                lines.append(f"[{cat}]:")
                lines.extend(items)
            knowledge_block = "\n".join(lines)
        else:
            knowledge_block = "(No KIS entries loaded — apply general domain principles.)"

        if not scenario_context:
            scenario_context = "(No past similar scenarios found.)"

        system_prompt = _MINISTER_INSTRUCTION.format(
            minister_name=self._display_name,
            persona_canon=self._persona,
            scenario_context=scenario_context,
            knowledge_context=knowledge_block,
        )

        prompt = f"Domains: {domain_hint}\n\nSituation: {user_input}"
        peer_info = context.get("peer_challenge") or context.get("peer_summary")
        if peer_info:
            prompt += f"\n\n---\n{peer_info}"

        try:
            raw = self.llm.analyze(system_prompt, prompt)
            return self._parse(raw)
        except Exception as e:
            return {
                "stance": "neutral",
                "reasoning": f"[{self.minister_name} unavailable: {e}]",
                "advice": f"[{self.minister_name} advice unavailable due to error]",
                "questions": [],
                "confidence": 0.3,
                "warning": "",
                "knowledge_cited": "",
                "fallback_triggered": True,
                "fallback_reasons": [f"Minister '{self.minister_name}' LLM call failed ({e}); defaulted to neutral stance."],
            }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "stance": "neutral",
            "reasoning": "",
            "advice": "",
            "questions": [],
            "confidence": 0.3,
            "warning": "",
            "knowledge_cited": "",
            "fallback_triggered": True,
            "fallback_reasons": [f"Minister '{self.minister_name}' received empty LLM response."],
        }

    def _parse(self, raw: str) -> Dict[str, Any]:
        """Parse JSON from LLM output, with robust fallback for reasoning models."""
        if not raw or not raw.strip():
            return self._empty_result()

        # Strip reasoning model thinking patterns
        cleaned = raw
        for prefix in ["Here's a thinking process:", "Here's my thinking:", "Let me think:", "Thinking:"]:
            if prefix in cleaned:
                idx = cleaned.index(prefix)
                # Find first { after the thinking prefix
                json_start = cleaned.find("{", idx)
                if json_start != -1:
                    cleaned = cleaned[json_start:]
                    break

        # Try direct JSON parse on cleaned text
        try:
            data = json.loads(cleaned.strip())
            return self._validate(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting JSON block from markdown fencing
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1))
                return self._validate(data)
            except Exception:
                pass

        # Try extracting any JSON object from the text (handle nested braces)
        brace_start = cleaned.find("{")
        if brace_start != -1:
            depth = 0
            for i in range(brace_start, len(cleaned)):
                if cleaned[i] == "{":
                    depth += 1
                elif cleaned[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(cleaned[brace_start:i+1])
                            return self._validate(data)
                        except Exception:
                            break

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
            "advice": raw[:200].strip(),
            "questions": [],
            "confidence": 0.5,
            "warning": "",
            "knowledge_cited": "",
            "fallback_triggered": True,
            "fallback_reasons": [f"Minister '{self.minister_name}' output non-JSON; fell back to heuristic text parsing."],
        }

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
        valid_stances = {"support", "oppose", "neutral"}
        stance = str(data.get("stance", "neutral")).lower()
        if stance not in valid_stances:
            stance = "neutral"
        reasoning = str(data.get("reasoning", ""))
        advice = str(data.get("advice", reasoning))
        raw_qs = data.get("questions", [])
        if isinstance(raw_qs, str):
            questions = [raw_qs] if raw_qs.strip() else []
        elif isinstance(raw_qs, list):
            questions = [str(q).strip() for q in raw_qs if str(q).strip()]
        else:
            questions = []
        return {
            "stance": stance,
            "reasoning": reasoning,
            "advice": advice,
            "questions": questions,
            "confidence": float(data.get("confidence", 0.5)),
            "warning": str(data.get("warning", "")),
            "knowledge_cited": str(data.get("knowledge_cited", "")),
            "fallback_triggered": False,
            "fallback_reasons": [],
        }
