from ingestion.v2.src.ollama_client import OllamaClient
c = OllamaClient()
print('Selected model:', c.model)
vec = c.embed('test embedding', timeout=10)
print('Embedding type:', type(vec), 'len=', len(vec) if hasattr(vec,'__len__') else 'N/A')
print('First 6 values:', vec[:6])
