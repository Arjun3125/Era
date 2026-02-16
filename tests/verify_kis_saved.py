import json

doc_file = r'C:\era\ingestion\v2\rag_storage\think-again-the-power-of-knowing-what-you-dont-know-random-house-large-print-grant-adam-z-lib.org_\02_doctrine.json'

with open(doc_file) as f:
    doctrines = json.load(f)

with_kis = sum(1 for d in doctrines if 'kis_guidance' in d)
print(f'RESULT: {with_kis}/{len(doctrines)} doctrines have kis_guidance')

if with_kis > 0:
    for d in doctrines:
        if 'kis_guidance' in d:
            chapter = d.get('chapter_index', '?')
            items = len(d['kis_guidance'])
            print(f'Example - Chapter {chapter}: {items} KIS items')
            if d['kis_guidance']:
                first = d['kis_guidance'][0][:100]
                print(f'First item: {first}...')
            break
else:
    print('No kis_guidance found')
    first_keys = list(doctrines[0].keys()) if doctrines else []
    print(f'First doctrine keys: {first_keys}')
