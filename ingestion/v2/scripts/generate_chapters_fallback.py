from ingestion.v2.src.pdf_extraction import extract_pdf_pages
from ingestion.v2.src.chapter_splitter import fallback_split_by_headings
import json, os, sys

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python generate_chapters_fallback.py <pdf_path>')
        sys.exit(1)
    pdf = sys.argv[1]
    book_id = os.path.splitext(os.path.basename(pdf))[0]
    storage = os.path.join('rag_storage', book_id)
    os.makedirs(storage, exist_ok=True)
    pages = extract_pdf_pages(pdf, storage=storage)
    canonical = '\f'.join(pages)
    with open(os.path.join(storage, '00_raw.txt'), 'w', encoding='utf-8') as f:
        f.write(canonical)
    chapters = fallback_split_by_headings(canonical)
    out_path = os.path.join(storage, '01_chapters.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(chapters, f, indent=2, ensure_ascii=False)
    print('WROTE', len(chapters), 'chapters to', out_path)
