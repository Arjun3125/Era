"""Clarification helpers."""

from __future__ import annotations

from typing import Any


def build_clarifying_question(situation: Any, state: Any) -> str:
    return "Could you share a bit more context so I can help?"


def format_question_for_user(question: str) -> str:
    return f"[Clarify] {question}"
