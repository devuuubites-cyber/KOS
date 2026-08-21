from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    chapter: str | None
    section: str | None
    page_start: int | None
    page_end: int | None
    sequence: int
    text: str

@dataclass
class Section:
    id: str
    title: str
    level: int
    chapter: str | None
    sequence: int
    page_start: int | None
    page_end: int | None

@dataclass
class BookMetadata:
    document_id: str
    title: str
    author: str | None
    file_name: str
    file_type: str
    imported_at: str
    processing_status: str = "IMPORTED"
    error: str | None = None
    page_count: int | None = None
    chapter_count: int = 0
    chunk_count: int = 0

@dataclass
class ExtractedDocument:
    metadata: BookMetadata
    chapters: list[Section] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    extracted_text_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": asdict(self.metadata),
            "chapters": [asdict(x) for x in self.chapters],
            "sections": [asdict(x) for x in self.sections],
            "chunks": [asdict(x) for x in self.chunks],
            "extracted_text_path": self.extracted_text_path,
        }
