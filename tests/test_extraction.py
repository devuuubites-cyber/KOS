import json
import pytest
from app.extraction import extract_chunk
from app.knowledge import SourceRef
from app.providers import LLMProvider, ModelRequest

class FakeProvider(LLMProvider):
    def __init__(self, payload): self.payload=payload; self.request=None
    def generate(self, request: ModelRequest): self.request=request; return json.dumps(self.payload)

SOURCE=SourceRef('b1','Test','Author','1','1.1',4,5,'c1','Losses loom larger than gains.')

def payload(source=SOURCE):
    from dataclasses import asdict
    return {'objects':[{'id':'k1','type':'principle','title':'Loss aversion','short_statement':'Losses loom larger than equivalent gains.','detailed_explanation':'','importance':5,'confidence':0.95,'domains':['psychology'],'tags':['bias'],'applications':['investing'],'prerequisites':[],'source':asdict(source),'knowledge_status':'SOURCE_DERIVED','claim_status':'AUTHOR_CLAIM','evidence':[],'related_objects':[],'contradicting_objects':[]}]}

def test_extraction_validates_and_preserves_provenance():
    provider=FakeProvider(payload())
    out=extract_chunk(provider,'source text',SOURCE,'test-model')
    assert out[0].source == SOURCE
    assert provider.request.role == 'extraction'
    assert provider.request.model == 'test-model'

def test_extraction_rejects_provenance_mismatch():
    other=SourceRef('other','Other','A','1','1',1,1,'x')
    with pytest.raises(ValueError, match='Provenance mismatch'):
        extract_chunk(FakeProvider(payload(other)),'source text',SOURCE)
