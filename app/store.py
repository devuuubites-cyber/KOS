from __future__ import annotations
import json, shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .config import ALLOWED_EXTENSIONS, BOOKS_DIR, MAX_UPLOAD_BYTES
from .ingestion import extract_book
from .models import BookMetadata

def utc_now(): return datetime.now(timezone.utc).isoformat()
def _book_dir(document_id): return BOOKS_DIR / document_id
def _write_json(path,payload): path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

def import_book(source: Path, original_name: str):
    suffix=source.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS: raise ValueError("Only .pdf and .epub files are supported.")
    if source.stat().st_size>MAX_UPLOAD_BYTES: raise ValueError("Book exceeds the 500 MB upload limit.")
    document_id=uuid4().hex; dest=_book_dir(document_id)
    (dest/"original").mkdir(parents=True); (dest/"extracted").mkdir(); (dest/"processing").mkdir()
    shutil.copy2(source,dest/"original"/f"original{suffix}")
    meta=BookMetadata(document_id,Path(original_name).stem,None,original_name,suffix[1:],utc_now()); _write_json(dest/"metadata.json",meta.__dict__); return meta

def process_book(document_id):
    dest=_book_dir(document_id); metadata_path=dest/"metadata.json"
    if not metadata_path.exists(): raise FileNotFoundError("Book not found.")
    meta=json.loads(metadata_path.read_text(encoding="utf-8")); original=next((p for p in (dest/"original").iterdir() if p.is_file()),None)
    if original is None: raise FileNotFoundError("Original book file is missing.")
    try:
        meta["processing_status"]="EXTRACTING"; _write_json(metadata_path,meta)
        full_text,blocks,count,extracted_meta,chapters,sections,chunks=extract_book(original)
        meta["title"]=extracted_meta.get("title") or meta["title"]; meta["author"]=extracted_meta.get("author"); meta["page_count"]=extracted_meta.get("pages") or count
        meta["chapter_count"]=len(chapters); meta["chunk_count"]=len(chunks); meta["processing_status"]="COMPLETE"; meta["error"]=None; _write_json(metadata_path,meta)
        for c in chunks:c.document_id=document_id
        (dest/"extracted"/"text.txt").write_text(full_text,encoding="utf-8")
        _write_json(dest/"extracted"/"structure.json",{"document_id":document_id,"chapters":[s.__dict__ for s in chapters],"sections":[s.__dict__ for s in sections],"chunks":[c.__dict__ for c in chunks]})
        _write_json(dest/"processing"/"result.json",{"status":"COMPLETE","completed_at":utc_now(),"blocks":len(blocks),"chapters":len(chapters),"sections":len(sections),"chunks":len(chunks)})
        return meta
    except Exception as exc:
        meta["processing_status"]="FAILED"; meta["error"]=f"{type(exc).__name__}: {exc}"; _write_json(metadata_path,meta); _write_json(dest/"processing"/"result.json",{"status":"FAILED","error":meta["error"]}); raise

def list_books():
    books=[]
    for d in sorted(BOOKS_DIR.iterdir() if BOOKS_DIR.exists() else [],key=lambda x:x.stat().st_mtime,reverse=True):
        p=d/"metadata.json"
        if d.is_dir() and p.exists(): books.append(json.loads(p.read_text(encoding="utf-8")))
    return books

def get_book(document_id):
    p=_book_dir(document_id)/"metadata.json"
    if not p.exists(): raise FileNotFoundError("Book not found.")
    meta=json.loads(p.read_text(encoding="utf-8")); structure=_book_dir(document_id)/"extracted"/"structure.json"
    if structure.exists(): meta["structure"]=json.loads(structure.read_text(encoding="utf-8"))
    return meta
