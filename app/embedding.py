from __future__ import annotations
from abc import ABC,abstractmethod
import math,re
class EmbeddingProvider(ABC):
    name='abstract'
    @abstractmethod
    def embed(self,text:str)->list[float]: raise NotImplementedError
class LocalHashEmbeddingProvider(EmbeddingProvider):
    '''Deterministic zero-dependency fallback. It is lexical, not a neural embedding.'''
    name='local-hash'
    def __init__(self,dimensions:int=256): self.dimensions=dimensions
    def embed(self,text:str)->list[float]:
        vec=[0.0]*self.dimensions
        for token in re.findall(r'[\\w-]+',text.lower()):
            h=hash(token)&0xffffffff; vec[h%self.dimensions]+=1.0
        norm=math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x/norm for x in vec]
def cosine(a:list[float],b:list[float])->float:
    if not a or not b or len(a)!=len(b): return 0.0
    return sum(x*y for x,y in zip(a,b))
