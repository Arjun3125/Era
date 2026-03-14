import subprocess, sys
# Skip in pytest unless explicitly enabled (requires local Ollama)
if "pytest" in sys.modules:
    import os
    import pytest

    if not os.getenv("ERA_RUN_OLLAMA_TESTS"):
        pytest.skip(
            "requires Ollama; set ERA_RUN_OLLAMA_TESTS=1 to run",
            allow_module_level=True,
        )
p = r'C:\era\rag_storage\Marcus-Aurelius-Meditations\00_raw.txt'
try:
    with open(p, 'r', encoding='utf-8') as f:
        txt = f.read()
except Exception as e:
    print('ERROR reading raw:', e); sys.exit(1)
page = txt.split('\f')[0]
page_text = page[:4000]
prompt = (
    "CURRENT BUFFER (tail only):\n" +
    "--------------------------\n\n" +
    "--------------------------\n\n" +
    "NEW PAGE TEXT:\n--------------------------\n" + page_text + "\n--------------------------\n\n" +
    "QUESTION:\nDoes this page START a new chapter, CONTINUE the current chapter, or END the current chapter?\n\n" +
    "Return JSON exactly:\n{\n  \"decision\": \"start_new_chapter | continue_chapter | end_chapter\",\n  \"confidence\": 0.0\n}\n"
)
model = "qwen2.5:0.5b"
cmd = ["ollama", "run", model, prompt]
print(f'CMD: ollama run {model} <prompt>')
proc = subprocess.run(cmd, capture_output=True, text=False, timeout=60)
stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
stderr = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else ''
print('returncode=', proc.returncode)
print('---STDOUT---')
print(stdout[:8000])
print('---STDERR---')
print(stderr[:8000])
