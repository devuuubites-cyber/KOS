from __future__ import annotations
import json
from .knowledge import KnowledgeObject, validate_knowledge

ALLOWED_TYPES = {'concept','definition','principle','claim','fact','mental_model','framework','method','procedure','heuristic','strategy','rule','example','case_study','evidence','argument','counterargument','warning','limitation','application','question'}

def parse_llm_objects(raw: str) -> list[KnowledgeObject]:
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get('objects')
    if not isinstance(data, list):
        raise ValueError('LLM output must be a JSON array or an object containing objects[].')
    objects=[]
    for item in data:
        if not isinstance(item, dict):
            raise ValueError('Every knowledge object must be a JSON object.')
        obj = KnowledgeObject(**item)
        if obj.type not in ALLOWED_TYPES:
            raise ValueError(f'Unsupported knowledge type: {obj.type}')
        validate_knowledge(obj)
        if obj.knowledge_status == 'SOURCE_DERIVED' and obj.source is None:
            raise ValueError('Source-derived knowledge requires source provenance.')
        objects.append(obj)
    return objects

EXTRACTION_INSTRUCTIONS = '''Extract atomic, reusable knowledge from this source chunk. Do not produce a generic summary. Preserve the author's uncertainty and distinguish author claims from facts. Never invent evidence, citations, page numbers, or applications. Every SOURCE_DERIVED object must use the supplied source provenance. Return JSON only as {"objects":[...]} .'''
