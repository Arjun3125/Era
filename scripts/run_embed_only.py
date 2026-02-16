import asyncio, os, sys
sys.path.insert(0, r'C:\era')
from ingestion.v2.src.ingest_pipeline import _parse_chunks_from_file
from ingestion.v2.src.async_ingest_orchestrator import AsyncIngestionPipeline
from ingestion.v2.src.ollama_client import OllamaClient
from ingestion.v2.src.config import DEFAULT_EMBED_MODEL

nodes = r'C:\era\rag_storage\Deep Work\03_nodes_chunks.json'
print('Nodes exists', os.path.exists(nodes))

embed_client = OllamaClient(model=DEFAULT_EMBED_MODEL)

async def run_once():
    pipeline = AsyncIngestionPipeline(db_dsn=None, output_root=r'C:\era\rag_storage\Deep Work\ministers', llm_client=embed_client)
    metrics = await pipeline.run(book_paths=[nodes], parse_func=_parse_chunks_from_file, num_embed_workers=1)
    print('Pipeline metrics:', metrics)

if __name__ == '__main__':
    asyncio.run(run_once())
