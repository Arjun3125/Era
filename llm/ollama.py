"""Local shim for Ollama CLI to satisfy persona.ollama_runtime imports.

Provides minimal `list()` and `chat()` functions used by the persona package.
This avoids needing a separate Python `ollama` package and calls the installed
`ollama` CLI instead. Output is decoded with replacement to avoid decoding errors.
"""
import subprocess

def list():
    """Run `ollama list` to verify the daemon is reachable. Raises on failure."""
    try:
        subprocess.run(["ollama", "list"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as e:
        raise

def chat(model, messages):
    """Run a simple chat by concatenating messages and sending to `ollama run <model>`.

    Returns a dict with the same shape expected by persona.ollama_runtime.chat:
    {"message": {"content": <assistant text>}}
    """
    # Build a simple text prompt from the message list
    prompt_parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        prompt_parts.append(f"{role.upper()}: {content}")
    prompt = "\n".join(prompt_parts)

    try:
        p = subprocess.run(["ollama", "run", model], input=prompt.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assistant = p.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        assistant = f"[ollama CLI error: {e}]"

    return {"message": {"content": assistant}}
