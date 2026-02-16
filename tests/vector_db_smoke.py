import sys
sys.path.insert(0, r'c:\era\ingestion\v2\src')
from vector_db import VectorDBStub

v = VectorDBStub(storage_root='data')
emb = [0.1] * 1536
eid = v.insert_combined('base', 'principles', 'test text', emb, source_book='bookx', source_chapter=1)
print('INSERTED', eid)
try:
    v.insert_domain('base', 'principles', 'test text', emb)
except Exception as e:
    print('DOMAIN_INSERT_ERR', e)
res = v.search_combined(emb, topk=1)
print('FOUND', len(res))
res2 = v.search_domain('base', emb, topk=1)
print('FOUND_DOMAIN', len(res2))
