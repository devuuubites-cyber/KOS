from __future__ import annotations
from typing import Any
from .config import DB_PATH
from .storage import Store
from .retrieval import hybrid_search

def retrieve(query:str,limit:int=8)->dict[str,Any]:
    query=query.strip()
    if not query: raise ValueError('query cannot be empty')
    limit=max(1,min(int(limit),50)); db=Store(DB_PATH)
    try:
        rows=hybrid_search(db,query,limit); results=[]
        for r in rows:
            results.append({'id':r.get('id') or r.get('object_id'),'title':r.get('title'),'type':r.get('type'),'statement':r.get('short_statement') or r.get('text'),'explanation':r.get('detailed_explanation'),'importance':r.get('importance'),'relevance':r.get('hybrid_relevance',r.get('semantic_relevance')),'source':r.get('source_json')})
        return {'query':query,'results':results}
    finally: db.close()

def tool_manifest():
    return {'name':'KOS Local Knowledge Bridge','version':'1','local_only':True,'tools':[{'name':'search_knowledge','description':'Search the local knowledge library using hybrid retrieval.','inputSchema':{'type':'object','properties':{'query':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':50}},'required':['query']}},{'name':'get_related_knowledge','description':'Retrieve relationships for a knowledge object.','inputSchema':{'type':'object','properties':{'object_id':{'type':'string'}},'required':['object_id']}}]}
