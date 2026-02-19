import sys, os
sys.path.insert(0, r'C:\era\ingestion\v2')
from src.ingest_pipeline import run_full_ingest_with_resume

def validate_paths():
    """Validate required directories exist before processing."""
    books_dir = r'C:\era\data\books'
    era_root = r'C:\era'
    
    # Check ERA root
    if not os.path.exists(era_root):
        raise FileNotFoundError(f"ERA root directory not found: {era_root}")
    
    # Check books directory
    if not os.path.exists(books_dir):
        raise FileNotFoundError(f"Books directory not found: {books_dir}")
    
    # Check books directory is not empty
    pdf_files = [f for f in os.listdir(books_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        raise ValueError(f"No PDF files found in: {books_dir}")
    
    print(f"[OK] Path validation passed")
    print(f"     ERA Root: {era_root}")
    print(f"     Books Dir: {books_dir}")
    print(f"     PDF Count: {len(pdf_files)}")
    return books_dir

if __name__ == '__main__':
    try:
        books_dir = validate_paths()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    
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
