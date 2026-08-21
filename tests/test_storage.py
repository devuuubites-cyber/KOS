from pathlib import Path
from app.models import Section,Chunk
from app.storage import Store

def test_sqlite_roundtrip(tmp_path:Path):
    store=Store(tmp_path/'kos.db')
    store.save_book('b1','Test','Author','pdf','/tmp/original.pdf',{'pages':2})
    ch=Section('ch-1','Chapter 1',1,'Chapter 1',0,1,2)
    sec=Section('sec-1','Section 1',2,'Chapter 1',1,1,1)
    chunk=Chunk('chunk-1','b1','Chapter 1','Section 1',1,2,1,'Loss aversion means losses loom larger than gains.')
    store.save_structure('b1',[ch],[sec],[chunk])
    counts=store.counts('b1'); assert counts['chapters']==1 and counts['sections']==1 and counts['chunks']==1
    assert store.search_chunks('loss aversion')[0]['id']=='chunk-1'
    store.save_embeddings('chunk',[('chunk-1',[1.0,0.0])],'test','v1')
    assert store.get_embeddings('chunk','test','v1')[0][0]=='chunk-1'
    store.close()
