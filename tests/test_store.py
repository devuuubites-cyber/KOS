from app import store

def test_import_preserves_original(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'BOOKS_DIR',tmp_path/'books')
    source=tmp_path/'sample.pdf';source.write_bytes(b'%PDF-test')
    meta=store.import_book(source,'My Book.pdf')
    original=tmp_path/'books'/meta.document_id/'original'/'original.pdf'
    assert original.exists() and original.read_bytes()==b'%PDF-test'
