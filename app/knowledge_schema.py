from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

KnowledgeStatus = Literal["SOURCE_DERIVED", "INTERPRETATION", "SYSTEM_SYNTHESIS"]
EpistemicType = Literal["AUTHOR_CLAIM", "SOURCE_FACT", "SYSTEM_INTERPRETATION", "SYSTEM_SYNTHESIS"]

VALID_TYPES = {
    "concept", "definition", "principle", "claim", "fact", "mental_model", "framework",
    "method", "procedure", "heuristic", "strategy", "rule", "example", "case_study",
    "evidence", "argument", "counterargument", "warning", "limitation", "application", "question",
}

VALID_RELATIONSHIPS = {
    "related_to", "supports", "contradicts", "expands", "example_of", "application_of",
    "prerequisite_for", "causes", "caused_by", "analogous_to", "contrasts_with", "derived_from",
}


@dataclass
class SourceRef:
    document_id: str
    book: str
    author: str | None
    chapter: str | None
    section: str | None
    page_start: int | None
    page_end: int | None
    chunk_id: str
    excerpt: str | None = None


@dataclass
class KnowledgeObject:
    id: str
    type: str
    title: str
    short_statement: str
    detailed_explanation: str
    importance: int
    confidence: float
    domains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    source: SourceRef | None = None
    knowledge_status: KnowledgeStatus = "SOURCE_DERIVED"
    epistemic_type: EpistemicType = "AUTHOR_CLAIM"
    related_objects: list[str] = field(default_factory=list)
    contradicting_objects: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors=[]
        if self.type not in VALID_TYPES: errors.append(f"invalid type: {self.type}")
        if not self.title.strip(): errors.append("title is required")
        if not self.short_statement.strip(): errors.append("short_statement is required")
        if not self.detailed_explanation.strip(): errors.append("detailed_explanation is required")
        if not 1 <= self.importance <= 5: errors.append("importance must be 1..5")
        if not 0 <= self.confidence <= 1: errors.append("confidence must be 0..1")
        if self.knowledge_status == "SOURCE_DERIVED" and self.source is None: errors.append("SOURCE_DERIVED objects require a source")
        if self.knowledge_status == "SYSTEM_SYNTHESIS" and self.epistemic_type != "SYSTEM_SYNTHESIS": errors.append("SYSTEM_SYNTHESIS must use SYSTEM_SYNTHESIS epistemic_type")
        if self.source and (self.source.page_start is not None and self.source.page_end is not None and self.source.page_end < self.source.page_start): errors.append("source page range is invalid")
        return errors

    def to_dict(self):
        return asdict(self)


def validate_knowledge_object(obj: KnowledgeObject) -> KnowledgeObject:
    errors=obj.validate()
    if errors: raise ValueError("Knowledge object rejected: " + "; ".join(errors))
    return obj


def validate_relationship_type(value: str) -> str:
    if value not in VALID_RELATIONSHIPS: raise ValueError(f"Unsupported relationship type: {value}")
    return value
