import sys, os
sys.path.insert(0, r'C:\era\ingestion\v2')
from src.ingest_pipeline import run_full_ingest_with_resume

if __name__ == '__main__':
    books_dir = r'C:\era\data\books'
    files = sorted([f for f in os.listdir(books_dir) if f.lower().endswith('.pdf')])

    for fname in files:
        path = os.path.join(books_dir, fname)
        print('='*80)
        print('Processing:', fname)
        try:
            run_full_ingest_with_resume(path, resume=True)
        except Exception as e:
            print('ERROR processing', fname, e)
        print('Finished:', fname)

    print('All done')
