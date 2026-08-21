from __future__ import annotations
from .knowledge import KnowledgeObject,SourceRef,parse_llm_objects,extraction_prompt
from .providers import LLMProvider,ModelRequest

def build_extraction_request(chunk_text:str,source:SourceRef,model:str|None=None)->ModelRequest:
    return ModelRequest(role='extraction',prompt=extraction_prompt(chunk_text,source),context=chunk_text,model=model,temperature=0.0)

def extract_chunk(provider:LLMProvider,chunk_text:str,source:SourceRef,model:str|None=None)->list[KnowledgeObject]:
    raw=provider.generate(build_extraction_request(chunk_text,source,model))
    return parse_llm_objects(raw,expected_source=source)

def extract_chunks(provider:LLMProvider,chunks,document_id:str,book:str,author:str|None,model:str|None=None)->list[KnowledgeObject]:
    result=[]
    for chunk in chunks:
        cid=getattr(chunk,'chunk_id',getattr(chunk,'id',''))
        source=SourceRef(document_id,book,author,chunk.chapter,chunk.section,chunk.page_start,chunk.page_end,cid)
        result.extend(extract_chunk(provider,chunk.text,source,model))
    return result
