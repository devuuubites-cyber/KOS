from __future__ import annotations
from dataclasses import dataclass,asdict,field
from typing import Literal

KnowledgeType=Literal['concept','definition','principle','claim','fact','mental_model','framework','method','procedure','heuristic','strategy','rule','example','case_study','evidence','argument','counterargument','warning','limitation','application','question']
KnowledgeStatus=Literal['SOURCE_DERIVED','INTERPRETATION','SYSTEM_SYNTHESIS']
ClaimStatus=Literal['AUTHOR_CLAIM','SOURCE_FACT','SYSTEM_INTERPRETATION','SYSTEM_SYNTHESIS']

@dataclass
class SourceRef:
    document_id:str; book:str; author:str|None; chapter:str|None; section:str|None
    page_start:int|None; page_end:int|None; chunk_id:str; excerpt:str|None=None

@dataclass
class KnowledgeObject:
    id:str; type:KnowledgeType; title:str; short_statement:str; detailed_explanation:str
    importance:int; confidence:float; domains:list[str]=field(default_factory=list); tags:list[str]=field(default_factory=list)
    applications:list[str]=field(default_factory=list); prerequisites:list[str]=field(default_factory=list)
    source:SourceRef|None=None; knowledge_status:KnowledgeStatus='SOURCE_DERIVED'; claim_status:ClaimStatus='AUTHOR_CLAIM'
    evidence:list[str]=field(default_factory=list); related_objects:list[str]=field(default_factory=list)
    contradicting_objects:list[str]=field(default_factory=list)

def validate_knowledge(obj:KnowledgeObject):
    if not obj.id or not obj.title or not obj.short_statement: raise ValueError('Knowledge object requires id, title and short_statement.')
    if obj.importance not in range(1,6): raise ValueError('importance must be 1-5.')
    if not 0 <= obj.confidence <= 1: raise ValueError('confidence must be between 0 and 1.')
    if obj.knowledge_status=='SOURCE_DERIVED' and obj.source is None: raise ValueError('SOURCE_DERIVED objects require provenance.')
    return obj

def to_dict(obj:KnowledgeObject): return asdict(validate_knowledge(obj))
