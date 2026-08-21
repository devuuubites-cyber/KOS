from __future__ import annotations
from .semantic import make_provider,cosine
from .storage import Store
DEFAULT_MODEL='all-MiniLM-L6-v2'
def _provider_info(provider,model): return provider.__class__.__name__,model
def index_embeddings(db:Store,provider=None,model=DEFAULT_MODEL):
    provider=provider or make_provider(neural=True); pname,mname=_provider_info(provider,model)
    chunks=db.all_chunks(); texts=[c['text'] for c in chunks]
    if texts: db.save_embeddings('chunk',[(c['id'],v) for c,v in zip(chunks,provider.embed_many(texts))],pname,mname)
    knowledge=db.all_knowledge(); texts=[f"{k['title']} {k['short_statement']} {k['detailed_explanation']}" for k in knowledge]
    if texts: db.save_embeddings('knowledge',[(k['id'],v) for k,v in zip(knowledge,provider.embed_many(texts))],pname,mname)
    return len(chunks),len(knowledge)
def semantic_search(db:Store,query,owner_type='knowledge',limit=20,provider=None,model=DEFAULT_MODEL):
    provider=provider or make_provider(neural=True); pname,mname=_provider_info(provider,model); q=provider.embed(query)
    rows=db.all_knowledge() if owner_type=='knowledge' else db.all_chunks(); by_id={r['id']:r for r in rows}; scored=[]
    for oid,v in db.get_embeddings(owner_type,pname,mname):
        if oid in by_id and len(v)==len(q): scored.append((cosine(q,v),by_id[oid]))
    return [dict(row,semantic_relevance=round(score,6)) for score,row in sorted(scored,key=lambda x:x[0],reverse=True)[:limit]]
def hybrid_search(db:Store,query,limit=20,provider=None,model=DEFAULT_MODEL):
    lexical=db.search_knowledge(query,max(limit*3,20)); semantic=semantic_search(db,query,'knowledge',max(limit*3,20),provider,model)
    lr={r['id']:1/(i+1) for i,r in enumerate(lexical)}; sr={r['id']:1/(i+1) for i,r in enumerate(semantic)}; rows={r['id']:r for r in lexical+semantic}; scored=[]
    for oid,row in rows.items():
        out=dict(row); out['hybrid_relevance']=round(.4*lr.get(oid,0)+.6*sr.get(oid,0),6); scored.append(out)
    return sorted(scored,key=lambda r:r['hybrid_relevance'],reverse=True)[:limit]
