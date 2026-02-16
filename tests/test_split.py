import sys
# ensure ingestion package is importable when running tests from tests dir
sys.path.insert(0, r'C:\era\ingestion\v1')
from llm import OllamaClient, DEFAULT_EXTRACT_MODEL

p = r'C:\era\rag_storage\Marcus-Aurelius-Meditations\00_raw.txt'
try:
    with open(p, 'r', encoding='utf-8') as f:
        txt = f.read()
except Exception as e:
    print('ERROR reading raw:', e)
    txt = ''
pages = txt.split('\f') if txt else ['']
page = pages[0] if pages else ''
page_text = page[:4000]

prompt = (
    "CURRENT BUFFER (tail only):\n"
    "--------------------------\n"
    "\n"
    "--------------------------\n\n"
    "NEW PAGE TEXT:\n"
    "--------------------------\n"
    f"{page_text}\n"
    "--------------------------\n\n"
    "QUESTION:\n"
    "Does this page START a new chapter, CONTINUE the current chapter,\n"
    "or END the current chapter?\n\n"
    "Return JSON exactly:\n"
    "{\n  \"decision\": \"start_new_chapter | continue_chapter | end_chapter\",\n  \"confidence\": 0.0\n}\n"
)

print('---SENDING PROMPT (truncated)---')
print(prompt[:800])
print('---END PROMPT PREVIEW---')

client = OllamaClient(model=DEFAULT_EXTRACT_MODEL)
print('---BEGIN MODEL RAW OUTPUT---')
try:
    out = client.generate(prompt, temperature=0.0, timeout=60)
    print(out)
except Exception as e:
    print('---ERROR---')
    print(str(e))
print('---END MODEL RAW OUTPUT---')
