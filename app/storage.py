from __future__ import annotations
import json,sqlite3
from pathlib import Path
from .models import Chunk,Section
SCHEMA='''PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS books(id TEXT PRIMARY KEY,title TEXT,author TEXT,format TEXT NOT NULL,original_path TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chapters(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,title TEXT NOT NULL,sequence INTEGER NOT NULL,page_start INTEGER,page_end INTEGER);
CREATE TABLE IF NOT EXISTS sections(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,title TEXT NOT NULL,level INTEGER NOT NULL,chapter_title TEXT,sequence INTEGER NOT NULL,page_start INTEGER,page_end INTEGER);
CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,chapter TEXT,section TEXT,page_start INTEGER,page_end INTEGER,sequence INTEGER NOT NULL,text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge_objects(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,type TEXT NOT NULL,title TEXT NOT NULL,short_statement TEXT NOT NULL,detailed_explanation TEXT NOT NULL,importance INTEGER NOT NULL,confidence REAL NOT NULL,domains_json TEXT NOT NULL,tags_json TEXT NOT NULL,applications_json TEXT NOT NULL,source_json TEXT,knowledge_status TEXT NOT NULL,claim_status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS relationships(id TEXT PRIMARY KEY,from_object_id TEXT NOT NULL REFERENCES knowledge_objects(id) ON DELETE CASCADE,to_object_id TEXT NOT NULL REFERENCES knowledge_objects(id) ON DELETE CASCADE,type TEXT NOT NULL,UNIQUE(from_object_id,to_object_id,type));
CREATE TABLE IF NOT EXISTS embeddings(owner_type TEXT NOT NULL,owner_id TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,dimensions INTEGER NOT NULL,vector_json TEXT NOT NULL,PRIMARY KEY(owner_type,owner_id,provider,model));
CREATE TABLE IF NOT EXISTS processing_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,stage TEXT NOT NULL,status TEXT NOT NULL,detail TEXT,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED,book_id UNINDEXED,text);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(object_id UNINDEXED,book_id UNINDEXED,title,short_statement,detailed_explanation,tags);'''
class Store:
 def __init__(self,path:Path): path.parent.mkdir(parents=True,exist_ok=True); self.conn=sqlite3.connect(path); self.conn.row_factory=sqlite3.Row; self.conn.executescript(SCHEMA)
 def close(self): self.conn.close()
 def save_book(self,book_id,title,author,fmt,original_path,metadata): self.conn.execute('INSERT OR REPLACE INTO books(id,title,author,format,original_path,metadata_json) VALUES(?,?,?,?,?,?)',(book_id,title,author,fmt,original_path,json.dumps(metadata,ensure_ascii=False))); self.conn.commit()
 def save_structure(self,book_id,chapters:list[Section],sections:list[Section],chunks:list[Chunk]):
  for c in chapters:self.conn.execute('INSERT OR REPLACE INTO chapters VALUES(?,?,?,?,?,?)',(c.id,book_id,c.title,c.sequence,c.page_start,c.page_end))
  for s in sections:self.conn.execute('INSERT OR REPLACE INTO sections VALUES(?,?,?,?,?,?,?,?)',(s.id,book_id,s.title,s.level,s.chapter,s.sequence,s.page_start,s.page_end))
  for c in chunks:
   cid=getattr(c,'chunk_id',getattr(c,'id',None)); self.conn.execute('INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?,?,?)',(cid,book_id,c.chapter,c.section,c.page_start,c.page_end,c.sequence,c.text)); self.conn.execute('DELETE FROM chunks_fts WHERE chunk_id=?',(cid,)); self.conn.execute('INSERT INTO chunks_fts VALUES(?,?,?)',(cid,book_id,c.text))
  self.conn.commit()
 def save_knowledge(self,book_id,objects):
  ids={((o if isinstance(o,dict) else o.__dict__)['id']) for o in objects}
  for o in objects:
   data=o if isinstance(o,dict) else o.__dict__; source=data.get('source'); source=source.__dict__ if hasattr(source,'__dict__') else source
   self.conn.execute('INSERT OR REPLACE INTO knowledge_objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(data['id'],book_id,data['type'],data['title'],data['short_statement'],data['detailed_explanation'],data['importance'],data['confidence'],json.dumps(data.get('domains',[])),json.dumps(data.get('tags',[])),json.dumps(data.get('applications',[])),json.dumps(source),data.get('knowledge_status','SOURCE_DERIVED'),data.get('claim_status','AUTHOR_CLAIM')))
   self.conn.execute('DELETE FROM knowledge_fts WHERE object_id=?',(data['id'],)); self.conn.execute('INSERT INTO knowledge_fts VALUES(?,?,?,?,?,?)',(data['id'],book_id,data['title'],data['short_statement'],data['detailed_explanation'],' '.join(data.get('tags',[]))))
   for target in data.get('related_objects',[]):
    if target in ids:self.conn.execute('INSERT OR IGNORE INTO relationships VALUES(?,?,?,?)',(f'rel-{data["id"]}-{target}-related',data['id'],target,'related_to'))
   for target in data.get('contradicting_objects',[]):
    if target in ids:self.conn.execute('INSERT OR IGNORE INTO relationships VALUES(?,?,?,?)',(f'rel-{data["id"]}-{target}-contradicts',data['id'],target,'contradicts'))
  self.conn.commit()
 def save_embeddings(self,owner_type,items,provider,model):
  for owner_id,vector in items:self.conn.execute('INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?,?,?)',(owner_type,owner_id,provider,model,len(vector),json.dumps(vector,separators=(',',':'))))
  self.conn.commit()
 def get_embeddings(self,owner_type,provider,model): return [(r['owner_id'],json.loads(r['vector_json'])) for r in self.conn.execute('SELECT owner_id,vector_json FROM embeddings WHERE owner_type=? AND provider=? AND model=?',(owner_type,provider,model)).fetchall()]
 def relationships(self,object_id): return [dict(r) for r in self.conn.execute('SELECT * FROM relationships WHERE from_object_id=? OR to_object_id=?',(object_id,object_id)).fetchall()]
 def set_job(self,book_id,stage,status,detail=None): self.conn.execute('INSERT INTO processing_jobs(book_id,stage,status,detail) VALUES(?,?,?,?)',(book_id,stage,status,detail)); self.conn.commit()
 def latest_job(self,book_id,stage): return self.conn.execute('SELECT * FROM processing_jobs WHERE book_id=? AND stage=? ORDER BY id DESC LIMIT 1',(book_id,stage)).fetchone()
 def completed_stages(self,book_id): return {r['stage'] for r in self.conn.execute("SELECT stage FROM processing_jobs WHERE book_id=? AND status='COMPLETE' GROUP BY stage",(book_id,)).fetchall()}
 def search_chunks(self,query,limit=20): return [dict(r) for r in self.conn.execute('SELECT c.* FROM chunks_fts f JOIN chunks c ON c.id=f.chunk_id WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?',(query,limit)).fetchall()]
 def search_knowledge(self,query,limit=20): return [dict(r) for r in self.conn.execute('SELECT k.* FROM knowledge_fts f JOIN knowledge_objects k ON k.id=f.object_id WHERE knowledge_fts MATCH ? ORDER BY bm25(knowledge_fts) LIMIT ?',(query,limit)).fetchall()]
 def all_chunks(self): return [dict(r) for r in self.conn.execute('SELECT * FROM chunks ORDER BY book_id,sequence').fetchall()]
 def all_knowledge(self): return [dict(r) for r in self.conn.execute('SELECT * FROM knowledge_objects').fetchall()]
 def counts(self,book_id): return {k:self.conn.execute(f'SELECT COUNT(*) FROM {k} WHERE book_id=?',(book_id,)).fetchone()[0] for k in ('chapters','sections','chunks','knowledge_objects')}
