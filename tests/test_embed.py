import sys
import os
import requests

# Skip in pytest unless explicitly enabled (requires local Ollama)
if "pytest" in sys.modules:
    import pytest

    if os.getenv("ERA_RUN_OLLAMA_TESTS", "").lower() not in ("1", "true", "yes"):
        pytest.skip(
            "requires Ollama; set ERA_RUN_OLLAMA_TESTS=1 to run",
            allow_module_level=True,
        )
    if os.getenv("ERA_RUN_LONG_LLM_TESTS", "").lower() not in ("1", "true", "yes"):
        pytest.skip(
            "long-running LLM test; set ERA_RUN_LONG_LLM_TESTS=1 to run",
            allow_module_level=True,
        )
u='http://localhost:11434/api/embed'
payload={'model':'llama3.1:8b-instruct-q4_0','input':'test embedding'}
try:
    r=requests.post(u,json=payload,timeout=10)
    print('status',r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text[:200])
except Exception as e:
    print('ERROR',e)
