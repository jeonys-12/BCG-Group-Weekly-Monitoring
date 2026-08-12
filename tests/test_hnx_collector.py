from datetime import date
from pathlib import Path
from src.collectors.hnx import HNXCollector
from tests.helpers import FakeResponse

FIXTURE=Path(__file__).parent/'fixtures'/'collectors'/'hnx'/'issuer.html'
class HTTP:
    def __init__(self): self.posts=[]
    def get(self,url,**kwargs): return FakeResponse(url,FIXTURE.read_text(encoding='utf-8'))
    def post_form(self,url,*,data,**kwargs): self.posts.append(data); return FakeResponse(url,FIXTURE.read_text(encoding='utf-8'))
def test_hnx_parser_pagination_and_exchange_contract():
    http=HTTP(); c=HNXCollector(http,{'base_url':'https://www.hnx.vn','issuer_page_template':'https://www.hnx.vn/vi-vn/m-tim-kiem-{ticker}.html','disclosure_page_path':'/ModuleMobile/MobileIssuer/ChangePageTCB','tickers':['BCG','BCR'],'max_pages':2})
    result=c.collect(date(2026,8,7),date(2026,8,7))
    assert result.status.value=='SUCCESS' and len(result.items)==2
    assert {i.source_type for i in result.items}=={'EXCHANGE'}
    assert http.posts[0]=={'StockCode':'BCG','MarketCode':'UC','Page':'2'}
    assert result.items[0].attachments[0].url.startswith('https://cims.hnx.vn/')
def test_hnx_schema_failure_is_not_empty_success():
    class Bad(HTTP):
        def get(self,url,**kwargs): return FakeResponse(url,'<html></html>')
    r=HNXCollector(Bad(),{'base_url':'https://www.hnx.vn','issuer_page_template':'https://www.hnx.vn/{ticker}','disclosure_page_path':'/post','tickers':['BCG']}).collect(date(2026,1,1),date(2026,1,2))
    assert r.status.value=='FAILED' and r.errors