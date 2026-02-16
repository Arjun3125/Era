import json

doc_path = r'C:\era\ingestion\v2\rag_storage\20090526_TNA13Crawford2009\02_doctrine.json'

with open(doc_path) as f:
    doctrines = json.load(f)

with_kis = sum(1 for d in doctrines if 'kis_guidance' in d)
print(f'kis_guidance found: {with_kis}/{len(doctrines)}')

if with_kis > 0:
    for d in doctrines:
        if 'kis_guidance' in d:
            print(f'Chapter {d.get("chapter_index")}: {len(d.get("kis_guidance", []))} items')
            print(f'First item: {d["kis_guidance"][0][:80]}...')
            break
else:
    print('No kis_guidance fields found in any doctrine')
    print('First doctrine keys:', list(doctrines[0].keys()) if doctrines else 'empty')
