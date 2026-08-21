from pathlib import Path
from app.models import Book
from app.storage import Store

def test_sqlite_roundtrip(tmp_path: Path):
    store=Store(tmp_path/'kos.db')
    book=Book('b1','Test','Author','pdf')
    store.save_book(book,'/tmp/original.pdf',{'pages':2})
    from app.models import Section, Chunk
    ch=Section('ch-1','Chapter 1',1,'Chapter 1',0,1,2)
    sec=Section('sec-1','Section 1',2,'Chapter 1',1,1,1)
    chunk=Chunk('chunk-1','b1','Chapter 1','Section 1',1,2,1,'Loss aversion means losses loom larger than gains.')
    store.save_structure('b1',[ch],[sec],[chunk])
    assert store.counts('b1') == {'chapters':1,'sections':1,'chunks':1}
    assert store.search_chunks('loss aversion')[0]['id']=='chunk-1'
    store.close()
