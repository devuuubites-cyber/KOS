from pathlib import Path
import shutil,tempfile
from fastapi import BackgroundTasks,FastAPI,File,HTTPException,UploadFile
from fastapi.responses import FileResponse,JSONResponse,PlainTextResponse
from fastapi.staticfiles import StaticFiles
from .config import STATIC_DIR,DB_PATH
from .store import get_book,import_book,list_books,process_book,search
from .storage import Store
from .retrieval import index_embeddings,semantic_search,hybrid_search
app=FastAPI(title='KOS — Personal Knowledge OS',version='0.6.0'); app.mount('/static',StaticFiles(directory=STATIC_DIR),name='static')
@app.get('/',include_in_schema=False)
def index(): return FileResponse(STATIC_DIR/'index.html')
@app.get('/api/health')
def health(): return {'status':'ok','mode':'local','version':app.version,'storage':'sqlite','search':['keyword','semantic','hybrid']}
@app.get('/api/books')
def books(): return list_books()
@app.get('/api/books/{document_id}')
def book(document_id):
    try:return get_book(document_id)
    except FileNotFoundError as exc: raise HTTPException(404,str(exc)) from exc
@app.get('/api/search')
def search_api(q:str,limit:int=20):
    if not q.strip(): raise HTTPException(400,'Query cannot be empty.')
    return {'query':q,'results':search(q,max(1,min(limit,100)))}
@app.get('/api/knowledge')
def knowledge(book_id:str|None=None,type:str|None=None,importance:int|None=None,limit:int=100):
    db=Store(DB_PATH)
    try:
        clauses=[]; args=[]
        if book_id: clauses.append('book_id=?'); args.append(book_id)
        if type: clauses.append('type=?'); args.append(type)
        if importance: clauses.append('importance=?'); args.append(importance)
        where=(' WHERE '+' AND '.join(clauses)) if clauses else ''
        rows=db.conn.execute('SELECT * FROM knowledge_objects'+where+' ORDER BY importance DESC,title LIMIT ?',(*args,max(1,min(limit,500)))).fetchall()
        return {'results':[dict(r) for r in rows]}
    finally: db.close()
@app.get('/api/knowledge/search')
def knowledge_search(q:str,limit:int=20):
    if not q.strip(): raise HTTPException(400,'Query cannot be empty.')
    db=Store(DB_PATH)
    try:return {'query':q,'results':db.search_knowledge(q,max(1,min(limit,100)))}
    finally:db.close()
@app.get('/api/knowledge/semantic-search')
def knowledge_semantic_search(q:str,limit:int=20):
    if not q.strip(): raise HTTPException(400,'Query cannot be empty.')
    db=Store(DB_PATH)
    try:return {'query':q,'results':semantic_search(db,q,limit=max(1,min(limit,100)))}
    finally:db.close()
@app.get('/api/knowledge/hybrid-search')
def knowledge_hybrid_search(q:str,limit:int=20):
    if not q.strip(): raise HTTPException(400,'Query cannot be empty.')
    db=Store(DB_PATH)
    try:return {'query':q,'results':hybrid_search(db,q,max(1,min(limit,100)))}
    finally:db.close()
@app.get('/api/knowledge/{object_id}/relationships')
def knowledge_relationships(object_id:str):
    db=Store(DB_PATH)
    try:return {'object_id':object_id,'relationships':db.relationships(object_id)}
    finally:db.close()
@app.get('/api/export/json')
def export_json():
    db=Store(DB_PATH)
    try:
        payload={t:[dict(r) for r in db.conn.execute(f'SELECT * FROM {t}').fetchall()] for t in ('books','chapters','sections','chunks','knowledge_objects','relationships')}
        return JSONResponse(payload,headers={'Content-Disposition':'attachment; filename=kos-export.json'})
    finally:db.close()
@app.get('/api/export/markdown')
def export_markdown():
    db=Store(DB_PATH)
    try:
        books=db.conn.execute('SELECT id,title,author FROM books ORDER BY title').fetchall(); lines=['# KOS Knowledge Export','']
        for b in books:
            lines += [f'## {b["title"]}',f'**Author:** {b["author"] or "Unknown"}','']
            rows=db.conn.execute('SELECT type,title,short_statement,detailed_explanation,importance,confidence,source_json,knowledge_status,claim_status FROM knowledge_objects WHERE book_id=? ORDER BY importance DESC,title',(b['id'],)).fetchall()
            for r in rows: lines += [f'### {r["title"]}',f'- **Type:** {r["type"]}',f'- **Importance:** {r["importance"]}/5',f'- **Confidence:** {r["confidence"]}',f'- **Status:** {r["knowledge_status"]}',f'- **Claim:** {r["claim_status"]}',f'\n{r["short_statement"]}',r["detailed_explanation"] or '',f'**Source:** {r["source_json"] or "Unavailable"}','']
        return PlainTextResponse('\n'.join(lines),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename=kos-export.md'})
    finally:db.close()
@app.post('/api/embeddings/index')
def embeddings_index():
    db=Store(DB_PATH)
    try:
        chunks,knowledge=index_embeddings(db); return {'status':'COMPLETE','chunks_indexed':chunks,'knowledge_indexed':knowledge}
    except Exception as exc: raise HTTPException(500,f'Embedding index failed: {type(exc).__name__}: {exc}') from exc
    finally:db.close()
@app.post('/api/books/import')
async def upload_book(file:UploadFile=File(...)):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.pdf','.epub'}: raise HTTPException(400,'Only PDF and EPUB files are supported.')
    with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tmp:
        tmp_path=Path(tmp.name); shutil.copyfileobj(file.file,tmp)
    try:return import_book(tmp_path,file.filename or 'book').__dict__
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    finally:tmp_path.unlink(missing_ok=True)
@app.post('/api/books/{document_id}/process')
def process(document_id,background_tasks:BackgroundTasks):
    try:get_book(document_id)
    except FileNotFoundError as exc: raise HTTPException(404,str(exc)) from exc
    background_tasks.add_task(process_book,document_id); return {'document_id':document_id,'status':'QUEUED'}
