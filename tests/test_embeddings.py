from app.embeddings import LocalSemanticEmbedding,cosine

def test_local_embedding_is_normalized_and_deterministic():
    p=LocalSemanticEmbedding(128); a=p.embed('loss aversion affects decisions'); b=p.embed('loss aversion affects decisions')
    assert a==b
    assert abs(cosine(a,a)-1)<1e-6

def test_different_texts_are_comparable():
    p=LocalSemanticEmbedding(128); assert len(p.embed('one'))==128; assert len(p.embed('two'))==128
