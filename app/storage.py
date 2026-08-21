from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .models import Chunk, Section

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS books(id TEXT PRIMARY KEY,title TEXT,author TEXT,format TEXT NOT NULL,original_path TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chapters(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,title TEXT NOT NULL,sequence INTEGER NOT NULL,page_start INTEGER,page_end INTEGER);
CREATE TABLE IF NOT EXISTS sections(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,title TEXT NOT NULL,level INTEGER NOT NULL,chapter_title TEXT,sequence INTEGER NOT NULL,page_start INTEGER,page_end INTEGER);
CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,chapter TEXT,section TEXT,page_start INTEGER,page_end INTEGER,sequence INTEGER NOT NULL,text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS processing_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,stage TEXT NOT NULL,status TEXT NOT NULL,detail TEXT,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED,book_id UNINDEXED,text);
'''

class Store:
    def __init__(self,path:Path):
        path.parent.mkdir(parents=True,exist_ok=True); self.conn=sqlite3.connect(path); self.conn.row_factory=sqlite3.Row; self.conn.executescript(SCHEMA)
    def close(self): self.conn.close()
    def save_book(self,book_id,title,author,fmt,original_path,metadata):
        self.conn.execute('INSERT OR REPLACE INTO books(id,title,author,format,original_path,metadata_json) VALUES(?,?,?,?,?,?)',(book_id,title,author,fmt,original_path,json.dumps(metadata,ensure_ascii=False))); self.conn.commit()
    def save_structure(self,book_id,chapters:list[Section],sections:list[Section],chunks:list[Chunk]):
        for c in chapters:self.conn.execute('INSERT OR REPLACE INTO chapters VALUES(?,?,?,?,?,?)',(c.id,book_id,c.title,c.sequence,c.page_start,c.page_end))
        for s in sections:self.conn.execute('INSERT OR REPLACE INTO sections VALUES(?,?,?,?,?,?,?,?)',(s.id,book_id,s.title,s.level,s.chapter,s.sequence,s.page_start,s.page_end))
        for c in chunks:
            self.conn.execute('INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?,?,?)',(c.chunk_id,book_id,c.chapter,c.section,c.page_start,c.page_end,c.sequence,c.text)); self.conn.execute('DELETE FROM chunks_fts WHERE chunk_id=?',(c.chunk_id,)); self.conn.execute('INSERT INTO chunks_fts VALUES(?,?,?)',(c.chunk_id,book_id,c.text))
        self.conn.commit()
    def set_job(self,book_id,stage,status,detail=None):
        self.conn.execute('INSERT INTO processing_jobs(book_id,stage,status,detail) VALUES(?,?,?,?)',(book_id,stage,status,detail)); self.conn.commit()
    def search_chunks(self,query,limit=20):
        rows=self.conn.execute('SELECT c.* FROM chunks_fts f JOIN chunks c ON c.id=f.chunk_id WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?',(query,limit)).fetchall(); return [dict(r) for r in rows]
    def counts(self,book_id): return {k:self.conn.execute(f'SELECT COUNT(*) FROM {k} WHERE book_id=?',(book_id,)).fetchone()[0] for k in ('chapters','sections','chunks')}
