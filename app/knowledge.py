from __future__ import annotations
from dataclasses import dataclass,asdict,field
from typing import Literal
import json
KnowledgeType=Literal['concept','definition','principle','claim','fact','mental_model','framework','method','procedure','heuristic','strategy','rule','example','case_study','evidence','argument','counterargument','warning','limitation','application','question']
KnowledgeStatus=Literal['SOURCE_DERIVED','INTERPRETATION','SYSTEM_SYNTHESIS']
ClaimStatus=Literal['AUTHOR_CLAIM','SOURCE_FACT','SYSTEM_INTERPRETATION','SYSTEM_SYNTHESIS']
@dataclass
class SourceRef:
    document_id:str; book:str; author:str|None; chapter:str|None; section:str|None; page_start:int|None; page_end:int|None; chunk_id:str; excerpt:str|None=None
@dataclass
class KnowledgeObject:
    id:str; type:KnowledgeType; title:str; short_statement:str; detailed_explanation:str; importance:int; confidence:float
    domains:list[str]=field(default_factory=list); tags:list[str]=field(default_factory=list); applications:list[str]=field(default_factory=list); prerequisites:list[str]=field(default_factory=list)
    source:SourceRef|None=None; knowledge_status:KnowledgeStatus='SOURCE_DERIVED'; claim_status:ClaimStatus='AUTHOR_CLAIM'; evidence:list[str]=field(default_factory=list); related_objects:list[str]=field(default_factory=list); contradicting_objects:list[str]=field(default_factory=list)
def validate_knowledge(obj:KnowledgeObject):
    if not obj.id or not obj.title.strip() or not obj.short_statement.strip(): raise ValueError('Knowledge object requires id, title and short_statement.')
    if obj.importance not in range(1,6): raise ValueError('importance must be 1-5.')
    if not 0<=obj.confidence<=1: raise ValueError('confidence must be between 0 and 1.')
    if obj.knowledge_status=='SOURCE_DERIVED' and obj.source is None: raise ValueError('SOURCE_DERIVED objects require provenance.')
    if obj.source and obj.source.page_start is not None and obj.source.page_start<1: raise ValueError('page_start must be positive.')
    return obj
def to_dict(obj:KnowledgeObject): return asdict(validate_knowledge(obj))
def parse_llm_objects(raw:str,expected_source:SourceRef|None=None)->list[KnowledgeObject]:
    try:data=json.loads(raw)
    except json.JSONDecodeError as e: raise ValueError(f'LLM returned invalid JSON: {e}') from e
    if isinstance(data,dict): data=data.get('objects',[])
    if not isinstance(data,list): raise ValueError('LLM output must be an array or objects wrapper.')
    result=[]
    for item in data:
        source=item.get('source')
        if source is not None and isinstance(source,dict): item['source']=SourceRef(**source)
        obj=KnowledgeObject(**item)
        if expected_source and obj.knowledge_status=='SOURCE_DERIVED' and (obj.source is None or obj.source.document_id!=expected_source.document_id or obj.source.chunk_id!=expected_source.chunk_id): raise ValueError(f'Provenance mismatch for {obj.id}.')
        result.append(validate_knowledge(obj))
    return result
def extraction_prompt(chunk_text:str,source:SourceRef)->str:
    return 'Extract atomic, reusable knowledge. Do not summarize. Never invent evidence. Preserve author attribution and uncertainty. Every SOURCE_DERIVED object must retain the supplied provenance. Return JSON only as {"objects":[...]}.\n\nSOURCE METADATA:\n'+json.dumps(asdict(source),ensure_ascii=False)+'\n\nSOURCE TEXT:\n'+chunk_text
