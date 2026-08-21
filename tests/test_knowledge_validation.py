import json
import pytest
from app.knowledge_validation import parse_llm_objects

SOURCE={'document_id':'b1','book':'Test','author':'Author','chapter':'1','section':'1.1','page_start':4,'page_end':5,'chunk_id':'c1','excerpt':'Losses loom larger than gains.'}

def valid_payload():
    return {'objects':[{'id':'k1','type':'principle','title':'Loss aversion','short_statement':'Losses loom larger than equivalent gains.','detailed_explanation':'','importance':5,'confidence':0.95,'domains':['psychology'],'tags':['behavioral-economics'],'applications':['investing'],'prerequisites':[],'source':SOURCE,'knowledge_status':'SOURCE_DERIVED','claim_status':'AUTHOR_CLAIM','evidence':[],'related_objects':[],'contradicting_objects':[]}]}

def test_valid_payload():
    objects=parse_llm_objects(json.dumps(valid_payload()))
    assert objects[0].source.chunk_id == 'c1'

def test_rejects_missing_source_for_source_derived():
    p=valid_payload(); p['objects'][0]['source']=None
    with pytest.raises(ValueError): parse_llm_objects(json.dumps(p))

def test_rejects_bad_importance():
    p=valid_payload(); p['objects'][0]['importance']=9
    with pytest.raises(ValueError): parse_llm_objects(json.dumps(p))
