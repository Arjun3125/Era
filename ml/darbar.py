"""DARBAR hierarchical debate helper.

Provides `darbar_debate` which runs multiple minister prompts and then
asks a sovereign to synthesize the final decision.
"""
from typing import Callable, List, Tuple

def darbar_debate(prompt: str, call_model_fn: Callable[[str, str], str], program_model: str, dry_run: bool = False) -> Tuple[List[str], str]:
    """Run multi-round minister debates and synthesize via sovereign.

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
        "You are Minister of Power.",
        "You are Minister of Timing.",
        "You are Minister of Psychology.",
        "You are Minister of Data & Intelligence.",
        "You are Minister of Diplomacy.",
    ]

    # Round 1: Initial stances
    r1_responses: List[str] = []
    for m in ministers:
        full_prompt = m + "\n\nProblem:\n" + prompt
        try:
            resp = call_model_fn(program_model, full_prompt)
        except Exception:
            resp = f"[DARBAR-FAULT] {m} failed to respond"
        r1_responses.append(resp)

    # Round 2: Peer challenge & debate
    r2_responses: List[str] = []
    peer_summary = "\n\n".join([f"{ministers[i]}: {r1_responses[i][:250]}" for i in range(len(ministers))])
    for i, m in enumerate(ministers):
        r2_prompt = (
            f"{m}\n\nProblem:\n{prompt}\n\n"
            f"Round 1 Cabinet Opinions:\n{peer_summary}\n\n"
            f"This is Round 2 (Peer Challenge & Advice Evolution). Converse directly with your fellow ministers! Critique their assumptions, trade-offs, or blind spots.\n"
            f"CRITICAL: You must actively EVOLVE your argument and formulate an actionable advice contribution by listening to your peers' constraints, while preserving your exact domain positioning (NO DRIFT from your core doctrine!). State how your advice evolves by addressing colleagues by name."
        )
        try:
            resp = call_model_fn(program_model, r2_prompt)
        except Exception:
            resp = r1_responses[i]
        r2_responses.append(f"[Round 1]: {r1_responses[i]}\n[Round 2 Evolved Advice & Rebuttal]: {resp}")

    sovereign_prompt = (
        "You are Sovereign.\nMinisters have debated across two full rounds of peer challenge and evolved their arguments without drifting from their domain positioning.\n"
        "Synthesize one unified, actionable strategic advice plan that incorporates each minister's evolved contribution, weighing all trade-offs and redlines.\n\n" + "\n\n".join(r2_responses)
    )

    try:
        final = call_model_fn(program_model, sovereign_prompt)
    except Exception:
        final = "[DARBAR-FAULT] Sovereign failed to synthesize decision"

    return r2_responses, final
