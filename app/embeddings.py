from __future__ import annotations
from dataclasses import dataclass
from abc import ABC, abstractmethod
import hashlib, math, re

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self,text:str)->list[float]: ...
    def embed_many(self,texts:list[str])->list[list[float]]: return [self.embed(t) for t in texts]

@dataclass
class LocalSemanticEmbedding(EmbeddingProvider):
    """Deterministic zero-install fallback; replaceable by a neural local model."""
    dimensions:int=768
    def embed(self,text:str)->list[float]:
        v=[0.0]*self.dimensions
        tokens=re.findall(r"[\w']+",text.lower())
        features=tokens+[" ".join(tokens[i:i+2]) for i in range(len(tokens)-1)]
        compact=re.sub(r'\s+',' ',text.lower().strip())
        features += [compact[i:i+5] for i in range(max(0,len(compact)-4))]
        for feature in features:
            h=hashlib.blake2b(feature.encode(),digest_size=16).digest()
            idx=int.from_bytes(h[:4],'little')%self.dimensions
            v[idx] += 1.0 if h[4]&1 else -1.0
        norm=math.sqrt(sum(x*x for x in v))
        return [x/norm for x in v] if norm else v

def cosine(a:list[float],b:list[float])->float:
    if len(a)!=len(b): raise ValueError('Embedding dimensions differ')
    return sum(x*y for x,y in zip(a,b))
