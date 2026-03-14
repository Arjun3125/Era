"""DARBAR hierarchical debate helper.

Provides `darbar_debate` which runs multiple minister prompts and then
asks a sovereign to synthesize the final decision.
"""
from typing import Callable, List, Tuple

def darbar_debate(prompt: str, call_model_fn: Callable[[str, str], str], program_model: str, dry_run: bool = False) -> Tuple[List[str], str]:
    """Run minister debates and synthesize via sovereign.

    Args:
        prompt: The core problem prompt.
        call_model_fn: Function taking (model, prompt) -> response string.
        program_model: Model name to call for ministers and sovereign.
        dry_run: If True, `call_model_fn` may still return canned outputs.

    Returns:
        (minister_responses, final_decision)
    """
    ministers = [
        "You are Minister of Strategy.",
        "You are Minister of Risk.",
        "You are Minister of Execution.",
    ]

    responses: List[str] = []

    for m in ministers:
        full_prompt = m + "\n\nProblem:\n" + prompt
        try:
            resp = call_model_fn(program_model, full_prompt)
        except Exception:
            # graceful fallback
            resp = f"[DARBAR-FAULT] {m} failed to respond"
        responses.append(resp)

    sovereign_prompt = (
        "You are Sovereign.\nMinisters have debated.\nSynthesize optimal decision.\n\n" + "\n\n".join(responses)
    )

    try:
        final = call_model_fn(program_model, sovereign_prompt)
    except Exception:
        final = "[DARBAR-FAULT] Sovereign failed to synthesize decision"

    return responses, final
