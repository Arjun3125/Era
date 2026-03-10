"""Baseline LLM runner for benchmark comparison."""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any, Dict


def build_baseline_prompt(scenario: Dict[str, Any]) -> str:
    options = "\n".join(f"- {item}" for item in scenario.get("decision_options", []))
    return "\n".join(
        [
            "Scenario:",
            scenario.get("prompt", ""),
            "",
            "Options:",
            options,
            "",
            "Choose the best option and explain why.",
            "Return format:",
            "Decision: <option>",
            "Confidence: <0-1>",
            "Reasoning: <short justification>",
        ]
    )


def run_llm_baseline(
    scenario: Dict[str, Any],
    *,
    provider: str = "none",
    model: str | None = None,
    temperature: float = 0.0,
    timeout_s: int = 60,
) -> Dict[str, Any]:
    provider = (provider or "none").strip().lower()
    if provider == "none":
        return {
            "status": "skipped",
            "provider": provider,
            "decision": "",
            "confidence": 0.0,
            "reasoning": "",
            "raw": "",
        }
    if provider == "ollama":
        if not model:
            raise ValueError("Ollama baseline requires --baseline-model.")
        prompt = build_baseline_prompt(scenario)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        request = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            text = str(data.get("response", ""))
        except json.JSONDecodeError:
            text = body
        parsed = parse_baseline_response(text, scenario)
        parsed.update({"status": "ok", "provider": provider, "raw": text})
        return parsed

    raise ValueError(f"Unsupported baseline provider: {provider}")


def parse_baseline_response(text: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
    decision_options = [str(item).strip().lower() for item in scenario.get("decision_options", [])]
    decision = ""
    confidence = 0.0

    decision_match = re.search(r"decision\s*:\s*(.+)", text, re.IGNORECASE)
    if decision_match:
        decision = decision_match.group(1).strip().lower()
    if decision and decision in decision_options:
        selected = decision
    else:
        selected = ""
        for option in decision_options:
            if option and option in text.lower():
                selected = option
                break
    confidence_match = re.search(r"confidence\s*:\s*([0-1](?:\.\d+)?)", text, re.IGNORECASE)
    if confidence_match:
        try:
            confidence = float(confidence_match.group(1))
        except ValueError:
            confidence = 0.0
    reasoning_match = re.search(r"reasoning\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else text.strip()

    return {
        "decision": selected,
        "confidence": max(0.0, min(1.0, confidence)),
        "reasoning": reasoning,
    }
