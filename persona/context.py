# persona/context.py
from pathlib import Path
from .trace import trace

MODE_VISIBLE_HINT = {
    "quick": "Casual conversation.",
    "war": "I’ll be blunt.",
    "meeting": "Let’s treat this like a structured discussion.",
    "darbar": "This deserves deeper, multi-perspective thinking.",
}

MODE_INERTIA = {
    "quick": 1,
    "war": 3,
    "meeting": 2,
    "darbar": 4,
}


def build_system_context(state) -> str:
    # Load persona/doctrine from external YAML if present
    doctrine_path = Path(__file__).resolve().parent.parent / "doctrine" / "persona.yaml"
    identity = ""
    if doctrine_path.exists():
        try:
            import yaml
            with open(doctrine_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            persona_canon = ""
            if isinstance(data, dict):
                persona_canon = data.get("persona", {}).get("canon", "")
                doctrine_purpose = data.get("doctrine", {}).get("purpose", "")
                identity = (persona_canon or "") + ("\n\n" + doctrine_purpose if doctrine_purpose else "")
            else:
                identity = str(data)
        except Exception:
            try:
                with open(doctrine_path, "r", encoding="utf-8") as f:
                    identity = f.read()
            except Exception:
                identity = ""
    else:
        identity = ""

    base = identity + "\n" if identity else ""

    NO_SELF_DESCRIPTION = (
        "You never explain who you are or what your role is. "
        "Speak directly to the situation at hand."
    )

    # Suppress exploratory questions in quick mode when user frequency is low/medium
    allow_questions = True
    try:
        if state.mode == "quick" and getattr(state, "user_frequency", "medium") in {"low", "medium"}:
            allow_questions = False
    except Exception:
        allow_questions = True

    QUESTION_SUPPRESSION = ""
    if not allow_questions:
        QUESTION_SUPPRESSION = (
            "\nDo not ask reflective or exploratory questions. "
            "Respond with short, grounded statements."
        )

    MODE_CONSTRAINTS = {
        "quick": (
            "This is a one-to-one conversation. "
            "Be natural, empathetic, and exploratory. "
            "You may ask questions to understand better."
        ),
        "war": (
            "Your goal is optimal outcome and correctness. "
            "Be blunt, decisive, and opinionated. "
            "Avoid unnecessary questions. "
            "Focus on what should be done."
        ),
        "meeting": (
            "You are preparing to work with multiple expert perspectives. "
            "Acknowledge that a structured discussion is appropriate, "
            "but note that full execution is not yet active."
        ),
        "darbar": (
            "You are preparing for deep council-level reasoning. "
            "Acknowledge the need for broader deliberation, "
            "but note that full darbar execution is not active."
        ),
    }

    if state.mode == "war":
        QUESTION_SUPPRESSION = "\nDo not ask reflective or exploratory questions. Respond with short, directive guidance."

    # Inject background synthesized knowledge if present (internal-only: not meant to be narrated)
    background = ""
    try:
        if getattr(state, "background_knowledge", None):
            bk = state.background_knowledge or {}
            # keep concise; will be used by the LLM silently to bias outputs
            background = "\n\nBACKGROUND_KNOWLEDGE (internal):\n"
            for i, item in enumerate(bk.get("synthesized_knowledge", [])[:5], start=1):
                background += f"- {item}\n"
            trace("context_injected_background", {"count": len(bk.get("synthesized_knowledge", []))})
    except Exception:
        background = ""

    ctx = base + NO_SELF_DESCRIPTION + QUESTION_SUPPRESSION + "\n" + MODE_CONSTRAINTS.get(state.mode, "")
    if background:
        ctx = ctx + "\n" + background
    return ctx


def trim_response(text: str, mode: str) -> str:
    if mode in {"war", "quick"}:
        lines = text.splitlines()
        return "\n".join(lines[:2]) if lines else text
    return text


def estimate_user_frequency(text: str) -> str:
    s = text.strip()
    words = len(s.split())
    if words <= 3:
        return "low"
    if words <= 12:
        return "medium"
    return "high"


def enforce_frequency(response: str, frequency: str) -> str:
    lines = response.strip().splitlines()
    if frequency == "low":
        return lines[0] if lines else response
    if frequency == "medium":
        return "\n".join(lines[:2]) if lines else response
    return response