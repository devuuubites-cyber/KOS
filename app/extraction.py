from __future__ import annotations
from dataclasses import asdict
from .knowledge import KnowledgeObject, SourceRef, validate_knowledge
from .knowledge_validation import EXTRACTION_INSTRUCTIONS, parse_llm_objects
from .providers import LLMProvider, ModelRequest


def build_extraction_request(chunk_text: str, source: SourceRef, model: str | None = None) -> ModelRequest:
    provenance = asdict(source)
    prompt = f'''{EXTRACTION_INSTRUCTIONS}\n\nSOURCE PROVENANCE:\n{provenance}\n\nSOURCE CHUNK:\n{chunk_text}'''
    return ModelRequest(role='extraction', prompt=prompt, context=chunk_text, model=model, temperature=0.0)


def extract_chunk(provider: LLMProvider, chunk_text: str, source: SourceRef, model: str | None = None) -> list[KnowledgeObject]:
    request = build_extraction_request(chunk_text, source, model)
    raw = provider.generate(request)
    objects = parse_llm_objects(raw)
    for obj in objects:
        if obj.knowledge_status == 'SOURCE_DERIVED' and obj.source != source:
            raise ValueError(f'Provenance mismatch for knowledge object {obj.id}')
        validate_knowledge(obj)
    return objects
