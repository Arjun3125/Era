import sys
sys.path.insert(0, r'C:\era\ingestion\v1')
from ingest import PHASE1_SYSTEM_PROMPT
from llm import OllamaClient

p = r'C:\era\rag_storage\Marcus-Aurelius-Meditations\00_raw.txt'
try:
    with open(p, 'r', encoding='utf-8') as f:
        txt = f.read()
except Exception as e:
    print('ERROR reading raw:', e)
    txt = ''
page = txt.split('\f')[0] if txt else ''
page_text = page[:4000]

user_prompt = f"""
CURRENT BUFFER (tail only):
--------------------------

--------------------------

NEW PAGE TEXT:
--------------------------
{page_text}
--------------------------

QUESTION:
Does this page START a new chapter, CONTINUE the current chapter,
or END the current chapter?

Return JSON exactly:
{
  "decision": "start_new_chapter | continue_chapter | end_chapter",
  "confidence": 0.0
}
"""

full = PHASE1_SYSTEM_PROMPT + "\n\n" + user_prompt
client = OllamaClient()
print('Calling qwen2.5-coder:latest...')
try:
    out = client.generate(full, model='qwen2.5-coder:latest', timeout=180)
    print('---MODEL OUTPUT START---')
    print(out)
    print('---MODEL OUTPUT END---')
except Exception as e:
    print('ERROR:', e)
