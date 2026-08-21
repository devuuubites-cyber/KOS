from app.retrieval import hybrid_search

def test_hybrid_search_empty_store_is_safe(tmp_path):
    from app.storage import Store
    db=Store(tmp_path/'kos.db')
    try:
        assert hybrid_search(db,'anything',limit=5)==[]
    finally: db.close()
