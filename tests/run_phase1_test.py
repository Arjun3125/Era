import sys
import os
import json
# ensure ingestion package is importable when running from tests dir
sys.path.insert(0, r'C:\era\ingestion\v1')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from ingest import extract_pdf_pages, split_chapters_with_ollama_streaming
from llm import OllamaClient

pdf = r"C:\era\data\books\Marcus-Aurelius-Meditations.pdf"
storage = r"C:\era\rag_storage\Marcus-Aurelius-Meditations"
os.makedirs(storage, exist_ok=True)

print(f"Loading PDF: {pdf}")
pages = extract_pdf_pages(pdf, storage=storage)
print(f"Extracted {len(pages)} pages")

client = OllamaClient()
print(f"Using model: {client.model}")
chapters = split_chapters_with_ollama_streaming(pages, client=client, book_title="Marcus Aurelius", storage=storage)
print(f"Produced {len(chapters)} chapters")

# write chapters summary
out = [{"chapter_index": c["chapter_index"], "chars": len(c.get("raw_text", ""))} for c in chapters]
with open(os.path.join(storage, "01_chapters_test.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(json.dumps(out, ensure_ascii=False, indent=2))
