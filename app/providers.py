from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
@dataclass(frozen=True)
class ModelRequest:
    role:str; prompt:str; context:str=''; model:str|None=None; temperature:float=0.0
class LLMProvider(ABC):
    name='abstract'
    @abstractmethod
    def generate(self,request:ModelRequest)->str: raise NotImplementedError
class LocalLLMProvider(LLMProvider):
    name='local'
    def __init__(self,endpoint='http://127.0.0.1:11434'): self.endpoint=endpoint.rstrip('/')
    def generate(self,request):
        import urllib.request
        payload=json.dumps({'model':request.model,'prompt':request.prompt+'\n'+request.context,'stream':False,'options':{'temperature':request.temperature}}).encode()
        req=urllib.request.Request(self.endpoint+'/api/generate',data=payload,headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=300) as r: return json.loads(r.read().decode())['response']
        except Exception as e: raise RuntimeError(f'Local LLM unavailable: {e}') from e
class CloudLLMProvider(LLMProvider):
    name='cloud'
    def __init__(self,api_key=None): self.api_key=api_key
    def generate(self,request): raise RuntimeError('No cloud vendor is enabled. Configure a concrete adapter explicitly before sending book text externally.')
@dataclass
class ModelRouting:
    fast_model:str|None=None; extraction_model:str|None=None; quality_model:str|None=None
    def for_role(self,role): return {'fast':self.fast_model,'extraction':self.extraction_model,'quality':self.quality_model}.get(role)
