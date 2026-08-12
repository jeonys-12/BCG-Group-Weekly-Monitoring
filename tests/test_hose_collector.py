import json
from datetime import date
from pathlib import Path
from src.collectors.hose import HOSECollector

FIXTURE=Path(__file__).parent/'fixtures'/'collectors'/'hose'/'news.json'
class Response:
    def __init__(self,url,payload,ctype='application/json'): self.url=url; self._payload=payload; self.content=json.dumps(payload).encode(); self.headers={'Content-Type':ctype}; self.status_code=200
    def raise_for_status(self): pass
    def json(self): return self._payload
class HTTP:
    def get(self,url,**kwargs): return Response(url,json.loads(FIXTURE.read_text(encoding='utf-8')))
def config(): return {'base_url':'https://www.hsx.vn','api_base_url':'https://api.hsx.vn/n/api/v1','disclosure_path':'/news/cate','category_alias':'thong-tin-cong-bo','tickers':['BCG'],'page_size':20,'max_pages':1}
def test_hose_official_json_contract_and_normalization():
    result=HOSECollector(HTTP(),config()).collect(date(2026,8,7),date(2026,8,7))
    assert result.status.value=='SUCCESS' and len(result.items)==1
    item=result.items[0]; assert item.source=='HOSE' and item.source_type=='EXCHANGE' and item.document_number=='123/QD-SGDHCM'
    assert item.attachments[0].url=='https://static.hsx.vn/files/123.pdf'
def test_hose_schema_and_content_type_fail_explicitly():
    class Bad:
        def get(self,url,**kwargs): return Response(url,{'data':{}},'text/html')
    result=HOSECollector(Bad(),config()).collect(date(2026,8,7),date(2026,8,7))
    assert result.status.value=='FAILED' and result.errors[0].code=='API_FETCH_OR_SCHEMA_FAILED'
def test_hose_fixture_contains_no_secret_fields():
    text=FIXTURE.read_text(encoding='utf-8').lower()
    assert all(word not in text for word in ('authorization','cookie','password','session'))