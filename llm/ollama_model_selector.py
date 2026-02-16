"""
Small helper to list installed Ollama models and pick two.

Functions:
- list_models(): returns list of model names (strings)
- select_models(preferred: list[str]|None): returns (user_model, program_model)

Behavior:
- If `ollama` CLI not found, returns empty list
- If fewer than 2 models installed, returns available ones and None for missing
- Prefers models listed in `preferred` if present
"""
import shutil
import subprocess
from typing import List, Tuple, Optional


def list_models() -> List[str]:
    """Return list of models from `ollama list`.

    If `ollama` CLI not available, returns [].
    """
    if shutil.which("ollama") is None:
        return []

    try:
        proc = subprocess.Popen(["ollama", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(timeout=10)
    except Exception:
        return []

    lines = [l.strip() for l in out.splitlines() if l.strip()]
    models = []
    for line in lines:
        # Typical output may be: "deepseek-r1:8b  (some meta)" or just name
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def select_models(preferred: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[str]]:
    """Select two models (user, program).

    preferred: list of model name prefixes to prefer, in order.
    Returns tuple (user_model, program_model) where elements may be None.
    """
    models = list_models()

    if not models:
        return (None, None)

    # try to satisfy preferred ordering
    if preferred:
        chosen = []
        for p in preferred:
            for m in models:
                if m.startswith(p) and m not in chosen:
                    chosen.append(m)
                    break
        # fill remaining from models
        for m in models:
            if m not in chosen:
                chosen.append(m)
        models = chosen

    user = models[0] if len(models) >= 1 else None
    program = models[1] if len(models) >= 2 else None

    return (user, program)


if __name__ == "__main__":
    print("Ollama models installed:")
    for m in list_models():
        print(" -", m)
    u, p = select_models()
    print("\nSelected:")
    print(" USER_MODEL:", u)
    print(" PROGRAM_MODEL:", p)
