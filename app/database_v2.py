from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS books (
 document_id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, file_name TEXT NOT NULL,
 file_type TEXT NOT NULL, original_path TEXT NOT NULL, imported_at TEXT NOT NULL,
 processing_status TEXT NOT NULL DEFAULT 'IMPORTED', error TEXT, page_count INTEGER,
 chapter_count INTEGER NOT NULL DEFAULT 0, chunk_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chapters (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES books(document_id) ON DELETE CASCADE,
 title TEXT NOT NULL, level INTEGER NOT NULL, sequence INTEGER NOT NULL, page_start INTEGER, page_end INTEGER
);
CREATE TABLE IF NOT EXISTS sections (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES books(document_id) ON DELETE CASCADE,
 chapter_id TEXT REFERENCES chapters(id) ON DELETE SET NULL, title TEXT NOT NULL, level INTEGER NOT NULL,
 sequence INTEGER NOT NULL, page_start INTEGER, page_end INTEGER
);
CREATE TABLE IF NOT EXISTS chunks (
 chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES books(document_id) ON DELETE CASCADE,
 chapter_id TEXT REFERENCES chapters(id) ON DELETE SET NULL, section_id TEXT REFERENCES sections(id) ON DELETE SET NULL,
 chapter TEXT, section TEXT, page_start INTEGER, page_end INTEGER, sequence INTEGER NOT NULL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_objects (
 id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL, short_statement TEXT NOT NULL,
 detailed_explanation TEXT NOT NULL, importance INTEGER NOT NULL CHECK(importance BETWEEN 1 AND 5),
 confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
 knowledge_status TEXT NOT NULL CHECK(knowledge_status IN ('SOURCE_DERIVED','INTERPRETATION','SYSTEM_SYNTHESIS')),
 epistemic_type TEXT NOT NULL CHECK(epistemic_type IN ('AUTHOR_CLAIM','SOURCE_FACT','SYSTEM_INTERPRETATION','SYSTEM_SYNTHESIS')),
 domains_json TEXT NOT NULL DEFAULT '[]', tags_json TEXT NOT NULL DEFAULT '[]', applications_json TEXT NOT NULL DEFAULT '[]',
 prerequisites_json TEXT NOT NULL DEFAULT '[]', source_document_id TEXT REFERENCES books(document_id) ON DELETE SET NULL,
 source_chunk_id TEXT REFERENCES chunks(chunk_id) ON DELETE SET NULL, source_chapter TEXT, source_section TEXT,
 page_start INTEGER, page_end INTEGER, source_excerpt TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relationships (
 id INTEGER PRIMARY KEY AUTOINCREMENT, from_object_id TEXT NOT NULL REFERENCES knowledge_objects(id) ON DELETE CASCADE,
 to_object_id TEXT NOT NULL REFERENCES knowledge_objects(id) ON DELETE CASCADE, relationship_type TEXT NOT NULL,
 confidence REAL CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 1), source TEXT NOT NULL DEFAULT 'SYSTEM',
 UNIQUE(from_object_id,to_object_id,relationship_type)
);
CREATE TABLE IF NOT EXISTS embeddings (
 object_id TEXT PRIMARY KEY REFERENCES knowledge_objects(id) ON DELETE CASCADE,
 provider TEXT NOT NULL, model TEXT NOT NULL, dimensions INTEGER NOT NULL, vector_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processing_jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL REFERENCES books(document_id) ON DELETE CASCADE,
 stage TEXT NOT NULL, status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 1),
 error TEXT, started_at TEXT, finished_at TEXT, UNIQUE(document_id,stage)
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
 object_id UNINDEXED, title, short_statement, detailed_explanation, tags, domains,
 content='knowledge_objects', content_rowid='rowid'
);
CREATE INDEX IF NOT EXISTS idx_chunks_document_sequence ON chunks(document_id,sequence);
CREATE INDEX IF NOT EXISTS idx_knowledge_document ON knowledge_objects(source_document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_objects(type);
CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_object_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_object_id);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute("INSERT INTO schema_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("schema_version", str(SCHEMA_VERSION)))

    def upsert_book(self, book: dict) -> None:
        fields=("document_id","title","author","file_name","file_type","original_path","imported_at","processing_status","error","page_count","chapter_count","chunk_count")
        placeholders=",".join("?" for _ in fields)
        updates=",".join(f"{f}=excluded.{f}" for f in fields[1:])
        with self.connect() as conn:
            conn.execute(f"INSERT INTO books({','.join(fields)}) VALUES({placeholders}) ON CONFLICT(document_id) DO UPDATE SET {updates}", tuple(book.get(f) for f in fields))

    def replace_structure(self, document_id: str, chapters: list[dict], sections: list[dict], chunks: list[dict]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM chapters WHERE document_id=?", (document_id,))
            chapter_ids={}
            for x in chapters:
                chapter_ids[x["title"]]=x["id"]
                conn.execute("INSERT INTO chapters(id,document_id,title,level,sequence,page_start,page_end) VALUES(?,?,?,?,?,?,?)", (x["id"],document_id,x["title"],x["level"],x["sequence"],x.get("page_start"),x.get("page_end")))
            section_ids={}
            for x in sections:
                section_ids[x["title"]]=x["id"]
                conn.execute("INSERT INTO sections(id,document_id,chapter_id,title,level,sequence,page_start,page_end) VALUES(?,?,?,?,?,?,?,?)", (x["id"],document_id,chapter_ids.get(x.get("chapter")),x["title"],x["level"],x["sequence"],x.get("page_start"),x.get("page_end")))
            for x in chunks:
                conn.execute("INSERT INTO chunks(chunk_id,document_id,chapter_id,section_id,chapter,section,page_start,page_end,sequence,text) VALUES(?,?,?,?,?,?,?,?,?,?)", (x["chunk_id"],document_id,chapter_ids.get(x.get("chapter")),section_ids.get(x.get("section")),x.get("chapter"),x.get("section"),x.get("page_start"),x.get("page_end"),x["sequence"],x["text"]))

    def add_processing_job(self, document_id: str, stage: str, status: str="PENDING", progress: float=0) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO processing_jobs(document_id,stage,status,progress) VALUES(?,?,?,?) ON CONFLICT(document_id,stage) DO UPDATE SET status=excluded.status,progress=excluded.progress,error=NULL", (document_id,stage,status,progress))

    def add_knowledge_object(self, obj: dict) -> None:
        with self.connect() as conn:
            values=(obj["id"],obj["type"],obj["title"],obj["short_statement"],obj["detailed_explanation"],obj["importance"],obj["confidence"],obj["knowledge_status"],obj["epistemic_type"],json.dumps(obj.get("domains",[])),json.dumps(obj.get("tags",[])),json.dumps(obj.get("applications",[])),json.dumps(obj.get("prerequisites",[])),obj.get("source_document_id"),obj.get("source_chunk_id"),obj.get("source_chapter"),obj.get("source_section"),obj.get("page_start"),obj.get("page_end"),obj.get("source_excerpt"),obj["created_at"])
            conn.execute("INSERT INTO knowledge_objects(id,type,title,short_statement,detailed_explanation,importance,confidence,knowledge_status,epistemic_type,domains_json,tags_json,applications_json,prerequisites_json,source_document_id,source_chunk_id,source_chapter,source_section,page_start,page_end,source_excerpt,created_at) VALUES("+",".join("?" for _ in values)+")", values)
            row=conn.execute("SELECT rowid FROM knowledge_objects WHERE id=?",(obj["id"],)).fetchone()
            conn.execute("INSERT INTO knowledge_fts(rowid,object_id,title,short_statement,detailed_explanation,tags,domains) VALUES(?,?,?,?,?,?,?)", (row[0],obj["id"],obj["title"],obj["short_statement"],obj["detailed_explanation"],json.dumps(obj.get("tags",[])),json.dumps(obj.get("domains",[]))))

    def search_knowledge(self, query: str, limit: int=20) -> list[dict]:
        with self.connect() as conn:
            rows=conn.execute("SELECT k.* FROM knowledge_fts f JOIN knowledge_objects k ON k.rowid=f.rowid WHERE knowledge_fts MATCH ? ORDER BY bm25(knowledge_fts) LIMIT ?",(query,limit)).fetchall()
            return [dict(r) for r in rows]
