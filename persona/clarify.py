"""
persona/clarify.py

Builds user-facing clarification prompts from a ControlDirective and state.
This implementation is defensive: it accepts generic objects and will
attempt to trace events using available `trace` functions when possible.
"""
from typing import Any, Optional, Sequence

from .trace import trace


def _trace_event(name: str, info: dict | None = None, src: Any = None) -> None:
    """Emit a trace event.
    
    Uses the global trace() function from trace.py.
    """
    try:
        trace(name, info or {})
    except Exception:
        # last resort: no-op
        pass


def build_clarifying_question(directive: Optional[Any], state: Optional[Any]) -> str:
    """Choose and format a clarifying question.

    Behavior:
    - If `directive.required_questions` exists and is non-empty, prefer the
      first question (or join the first two when multiple).
    - Otherwise return a short, safe generic clarifier asking for desired
      outcome and constraints.

    The function tolerates `directive` and `state` being None or arbitrary
    objects (suitable for iterative development of the persona runtime).
    """
    try:
        if directive is not None and hasattr(directive, "required_questions"):
            rq = getattr(directive, "required_questions")
            # Normalize to a sequence of strings
            if isinstance(rq, str):
                qs: Sequence[str] = [rq]
            elif isinstance(rq, Sequence):
                qs = [str(x) for x in rq if x]
            else:
                qs = []

            if qs:
                if len(qs) == 1:
                    q = qs[0]
                else:
                    # Keep the clarifier short when multiple required questions
                    q = " ".join(qs[:2])
                _trace_event("clarify_question_selected", {"question": q}, src=state or directive)
                return q.strip()
    except Exception as e:
        _trace_event("clarify_build_error", {"error": str(e)}, src=state or directive)

    # Generic fallback clarifier (short and actionable)
    fallback = "Can you say more about the outcome you want and the constraints that matter (time, money, people)?"
    _trace_event("clarify_question_fallback", {"question": fallback}, src=state)
    return fallback


def format_question_for_user(qobj: Any, state: Optional[Any] = None) -> str:
    """
    Format a question object or string into a short user-facing prompt.

    Behavior:
    - If `qobj` is a dict with a 'question' key, return it.
    - If `qobj` is a string, return it stripped.
    - Otherwise return a safe fallback asking for clarification.
    """
    try:
        if isinstance(qobj, str):
            q = qobj.strip()
            _trace_event("format_question_string", {"question": q}, src=state)
            return q

        if isinstance(qobj, dict):
            q = str(qobj.get("question") or qobj.get("q") or "").strip()
            if q:
                _trace_event("format_question_dict", {"question": q}, src=state)
                return q

    except Exception as e:
        _trace_event("format_question_error", {"error": str(e)}, src=state)

    fallback = "Can you say more about what you mean?"
    _trace_event("format_question_fallback", {"question": fallback}, src=state)
    return fallback
