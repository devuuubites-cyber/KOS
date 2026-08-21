from pathlib import Path
import sqlite3
from app.embeddings import LocalSemanticEmbedding,cosine
from app.ingestion import TextBlock,detect_structure,chunk_blocks
from app.storage import Store

def test_chunking_preserves_order_and_bounds():
    blocks=[TextBlock(f'Paragraph {i} ' + ('word '*80),1 if i<3 else 2,0,False,10) for i in range(8)]
    chunks=chunk_blocks(blocks,[],[],target_words=100,max_words=150)
    assert chunks
    assert [c.sequence for c in chunks]==list(range(1,len(chunks)+1))
    assert ''.join(c.text for c in chunks).count('Paragraph')==8
    assert all(len(c.text.split())<=150 for c in chunks)

def test_epub_heading_structure():
    blocks=[TextBlock('Chapter One',None,1,True),TextBlock('Body',None,0,False),TextBlock('Section A',None,2,True),TextBlock('Body 2',None,0,False)]
    chapters,sections=detect_structure(blocks)
    assert len(chapters)==1 and chapters[0].title=='Chapter One'
    assert len(sections)==1 and sections[0].title=='Section A'

def test_local_embedding_is_deterministic_and_normalized():
    p=LocalSemanticEmbedding(dimensions=128)
    a=p.embed('loss aversion affects decisions')
    b=p.embed('loss aversion affects decisions')
    assert a==b
    assert abs(cosine(a,a)-1)<1e-9
    assert len(a)==128

def test_sqlite_schema_and_search(tmp_path):
    db=Store(tmp_path/'kos.db')
    db.conn.execute("INSERT INTO books VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)",('b1','Test','Author','pdf','/tmp/x','{}'))
    db.conn.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)",('c1','b1','Chapter 1','Intro',1,1,1,'loss aversion decisions'))
    db.conn.execute("INSERT INTO chunks_fts VALUES(?,?,?)",('c1','b1','loss aversion decisions'))
    db.conn.commit()
    assert db.search_chunks('aversion')[0]['id']=='c1'
    db.close()
