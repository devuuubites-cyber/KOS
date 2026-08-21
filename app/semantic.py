from __future__ import annotations
from .embeddings import EmbeddingProvider, LocalSemanticEmbedding, cosine

class NeuralEmbeddingProvider(EmbeddingProvider):
    """Optional local sentence-transformers adapter; model files stay local after download."""
    def __init__(self,model_name='all-MiniLM-L6-v2'):
        from sentence_transformers import SentenceTransformer
        self.model=SentenceTransformer(model_name)
    def embed(self,text): return self.model.encode(text,normalize_embeddings=True).tolist()
    def embed_many(self,texts): return self.model.encode(texts,normalize_embeddings=True).tolist()

def make_provider(neural=False):
    if neural:
        try:return NeuralEmbeddingProvider()
        except Exception:return LocalSemanticEmbedding()
    return LocalSemanticEmbedding()

def rank(query,documents,provider=None,limit=20):
    provider=provider or make_provider(False); q=provider.embed(query); scored=[]
    for d in documents:
        text=' '.join(str(d.get(k,'')) for k in ('title','short_statement','detailed_explanation','text'))
        scored.append((cosine(q,provider.embed(text)),d))
    return [dict(d,semantic_relevance=round(score,6)) for score,d in sorted(scored,key=lambda x:x[0],reverse=True)[:limit]]
