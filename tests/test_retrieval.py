from app.storage import Store
from app.retrieval import semantic_search
from app.embeddings import LocalSemanticEmbedding
from app.models import Section,Chunk

def test_semantic_index_and_search(tmp_path):
    db=Store(tmp_path/'kos.db'); db.save_book('b','Book','Author','pdf','/tmp/b.pdf',{})
    db.save_structure('b',[Section('c','Chapter',1,'Chapter',0,1,1)],[],[Chunk('x','b','Chapter',None,1,1,1,'People dislike losses more than equivalent gains.')])
    n=LocalSemanticEmbedding(64); a=n.embed('loss aversion')
    db.save_embeddings('chunk',[('x',a)],n.__class__.__name__,'test')
    assert semantic_search(db,'loss aversion','chunk',provider=n,model='test')[0]['id']=='x'
    db.close()
