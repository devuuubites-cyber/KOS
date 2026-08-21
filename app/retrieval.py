from __future__ import annotations
from .semantic import make_provider,cosine
from .storage import Store

def index_embeddings(db:Store,provider=None,model='all-MiniLM-L6-v2'):
    provider=provider or make_provider(neural=True)
    chunks=db.all_chunks(); texts=[c['text'] for c in chunks]
    if texts:
        vectors=provider.embed_many(texts); db.save_embeddings('chunk',[(c['id'],v) for c,v in zip(chunks,vectors)],provider.__class__.__name__,model)
    knowledge=db.all_knowledge(); texts=[f"{k['title']} {k['short_statement']} {k['detailed_explanation']}" for k in knowledge]
    if texts:
        vectors=provider.embed_many(texts); db.save_embeddings('knowledge',[(k['id'],v) for k,v in zip(knowledge,vectors)],provider.__class__.__name__,model)
    return len(chunks),len(knowledge)

def semantic_search(db:Store,query,owner_type='knowledge',limit=20,provider=None,model='all-MiniLM-L6-v2'):
    provider=provider or make_provider(neural=True); q=provider.embed(query)
    rows=db.all_knowledge() if owner_type=='knowledge' else db.all_chunks(); by_id={r['id']:r for r in rows}
    vectors=db.get_embeddings(owner_type,provider.__class__.__name__,model); scored=[]
    for oid,v in vectors:
        if oid in by_id: scored.append((cosine(q,v),by_id[oid]))
    return [dict(row,semantic_relevance=round(score,6)) for score,row in sorted(scored,key=lambda x:x[0],reverse=True)[:limit]]

def hybrid_search(db:Store,query,limit=20,provider=None,model='all-MiniLM-L6-v2'):
    lexical=db.search_knowledge(query,max(limit*3,20)); semantic=semantic_search(db,query,'knowledge',max(limit*3,20),provider,model)
    merged={}
    for rank,row in enumerate(lexical): merged[row['id']]=[row,1/(rank+1),0.0]
    for rank,row in enumerate(semantic):
        if row['id'] not in merged: merged[row['id']]=[row,0.0,1/(rank+1)]
        else: merged[row['id']][2]=1/(rank+1)
    scored=[]
    for row,lex,sem in merged.values(): row=dict(row); row['hybrid_score']=round(0.4*lex+0.6*sem,6); scored.append(row)
    return sorted(scored,key=lambda r:r['hybrid_score'],reverse=True)[:limit]
