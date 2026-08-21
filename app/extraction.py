from __future__ import annotations
import re
from uuid import uuid4
from .knowledge import KnowledgeObject,SourceRef,parse_llm_objects,extraction_prompt,validate_knowledge
from .providers import LLMProvider,ModelRequest

def build_extraction_request(chunk_text:str,source:SourceRef,model:str|None=None)->ModelRequest:
    return ModelRequest(role='extraction',prompt=extraction_prompt(chunk_text,source),context=chunk_text,model=model,temperature=0.0)

def extract_chunk(provider:LLMProvider|None,chunk_text:str,source:SourceRef,model:str|None=None)->list[KnowledgeObject]:
    if provider is None:return heuristic_extract(chunk_text,source)
    raw=provider.generate(build_extraction_request(chunk_text,source,model))
    return parse_llm_objects(raw,expected_source=source)

def _title(s): return re.split(r'\s+(?:is|are|means|refers to)\s+',s,maxsplit=1,flags=re.I)[0].strip(' .,:;')[:120] or s[:120]
def heuristic_extract(text:str,source:SourceRef)->list[KnowledgeObject]:
    """Conservative offline candidate extractor. It never invents evidence and is not a substitute for an LLM."""
    out=[]
    for s in [x.strip() for x in re.split(r'(?<=[.!?])\s+',text) if 8<=len(x.split())<=80]:
        l=s.lower(); typ=None
        if re.search(r'\b(is|are|means|refers to)\b',l):typ='definition'
        elif re.search(r'\b(should|must|avoid|always|never|important to)\b',l):typ='principle'
        elif re.search(r'\b(study|experiment|research|data|percent|%)\b',l):typ='evidence'
        if typ:
            out.append(validate_knowledge(KnowledgeObject(f'k-{uuid4().hex}',typ,_title(s),s,s,3,0.62,source=source,knowledge_status='SOURCE_DERIVED',claim_status='AUTHOR_CLAIM')))
    return out[:30]

def extract_chunks(provider,chunks,document_id:str,book:str,author:str|None,model:str|None=None)->list[KnowledgeObject]:
    result=[]
    for chunk in chunks:
        cid=getattr(chunk,'chunk_id',getattr(chunk,'id',''))
        source=SourceRef(document_id,book,author,chunk.chapter,chunk.section,chunk.page_start,chunk.page_end,cid)
        result.extend(extract_chunk(provider,chunk.text,source,model))
    return result
