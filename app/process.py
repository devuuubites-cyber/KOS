from __future__ import annotations
import json, shutil, uuid
from pathlib import Path
from .ingestion import extract_book
from .models import Book
from .storage import Store

SUPPORTED={'.pdf','.epub'}

def process_book(source: Path, library: Path, db_path: Path):
    if source.suffix.lower() not in SUPPORTED: raise ValueError('Only PDF and EPUB are supported.')
    book_id=str(uuid.uuid4())
    book_dir=library/'books'/book_id
    original_dir=book_dir/'original'; extracted_dir=book_dir/'extracted'; processing_dir=book_dir/'processing'
    original_dir.mkdir(parents=True); extracted_dir.mkdir(); processing_dir.mkdir()
    original=original_dir/('original'+source.suffix.lower()); shutil.copy2(source,original)
    store=Store(db_path)
    try:
        store.set_job(book_id,'IMPORTING','COMPLETE')
        store.set_job(book_id,'EXTRACTING','RUNNING')
        text,blocks,count,meta,chapters,sections,chunks=extract_book(original)
        title=meta.get('title') or source.stem
        author=meta.get('author') or 'Unknown'
        book=Book(book_id,title,author,source.suffix.lower()[1:])
        metadata={**meta,'document_id':book_id,'source_filename':source.name,'block_count':len(blocks),'chapter_count':len(chapters),'section_count':len(sections),'chunk_count':len(chunks)}
        (extracted_dir/'text.txt').write_text(text,encoding='utf-8')
        (extracted_dir/'structure.json').write_text(json.dumps({'chapters':[c.__dict__ for c in chapters],'sections':[s.__dict__ for s in sections],'chunks':[c.__dict__ for c in chunks]},ensure_ascii=False,indent=2),encoding='utf-8')
        (book_dir/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        store.save_book(book,str(original),metadata)
        store.set_job(book_id,'EXTRACTING','COMPLETE')
        store.set_job(book_id,'CHUNKING','COMPLETE',f'{len(chunks)} chunks')
        store.save_structure(book_id,chapters,sections,chunks)
        store.set_job(book_id,'INDEXING','COMPLETE')
        result={'document_id':book_id,'title':title,'author':author,'format':book.format,'chapters':len(chapters),'sections':len(sections),'chunks':len(chunks),'original':str(original)}
        (processing_dir/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result
    finally: store.close()
