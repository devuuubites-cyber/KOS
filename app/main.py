from pathlib import Path
import shutil,tempfile,os
from fastapi import BackgroundTasks,FastAPI,File,HTTPException,UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import STATIC_DIR, DB_PATH
from .store import get_book,import_book,list_books,process_book,search
from .storage import Store
from .retrieval import index_embeddings,semantic_search,hybrid_search

app=FastAPI(title='KOS — Personal Knowledge OS',version='0.4.0')
app.mount('/static',StaticFiles(directory=STATIC_DIR),name='static')
@app.get('/',include_in_schema=False)
def index(): return FileResponse(STATIC_DIR/'index.html')
@app.get('/api/health')
def health(): return {'status':'ok','mode':'local','version':app.version,'embeddings':'local'}
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
@app.post('/api/embeddings/index')
def embeddings_index():
    db=Store(DB_PATH)
    try:
        chunks,knowledge=index_embeddings(db)
        return {'status':'COMPLETE','chunks_indexed':chunks,'knowledge_indexed':knowledge}
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
