import sys, os
sys.path.insert(0, r'C:\era\ingestion\v2')
from src.ingest_pipeline import run_full_ingest_with_resume as run_ingest

pdf = r'C:\era\data\books\Marcus-Aurelius-Meditations.pdf'
out = r'C:\era\rag_storage\Marcus-Aurelius-Meditations-v2-test'
os.makedirs(out, exist_ok=True)

print('Running v2 ingest test')
run_ingest(pdf, out)
print('v2 ingest test completed')
