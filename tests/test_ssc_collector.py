from datetime import date
from pathlib import Path
import requests
from src.collectors.ssc import SSCCollector
from tests.helpers import FakeResponse
BASE=Path(__file__).parent/'fixtures'/'collectors'/'ssc'
DETAIL='https://ssc.gov.vn/webcenter/portal/ubck/pages_r/l/chitit?dDocName=APPSSCGOVVN_BCG_001'
class HTTP:
    def get(self,url,**kwargs):
        if 'tintuc?' in url: return FakeResponse(url,(BASE/'list.html').read_text(encoding='utf-8'))
        if url==DETAIL: return FakeResponse(url,(BASE/'detail.html').read_text(encoding='utf-8'))
        raise requests.ConnectionError(url)
def config(): return {'base_url':'https://ssc.gov.vn','list_url':'https://ssc.gov.vn/webcenter/portal/ubck/pages_r/l/tintuc','detail_path':'/webcenter/portal/ubck/pages_r/l/chitit','entities':['BCG','Bamboo Capital','BCG Land'],'max_pages':1}
def test_ssc_webcenter_list_detail_and_ddocname_contract():
    result=SSCCollector(HTTP(),config()).collect(date(2026,8,7),date(2026,8,7))
    assert result.status.value=='SUCCESS' and len(result.items)==1
    item=result.items[0]; assert item.source_type=='REGULATOR' and item.company=='BCG Land'
    assert 'dDocName=APPSSCGOVVN_BCG_001' in item.url and item.attachments[0].url.startswith('https://ssc.gov.vn/cs/idcplg')
def test_ssc_detail_network_failure_is_partial_not_empty_success():
    class Bad(HTTP):
        def get(self,url,**kwargs):
            if 'tintuc?' in url: return super().get(url,**kwargs)
            raise requests.ConnectionError('offline')
    result=SSCCollector(Bad(),config()).collect(date(2026,8,7),date(2026,8,7))
    assert result.status.value=='PARTIAL' and result.errors[0].code=='DETAIL_FETCH_OR_SCHEMA_FAILED'
def test_ssc_false_positive_is_excluded():
    html=(BASE/'detail.html').read_text(encoding='utf-8').replace('BCG Land','ABCG Logistics')
    class FalsePositive(HTTP):
        def get(self,url,**kwargs):
            if 'tintuc?' in url: return super().get(url,**kwargs)
            return FakeResponse(url,html)
    result=SSCCollector(FalsePositive(),config()).collect(date(2026,8,7),date(2026,8,7))
    assert result.status.value=='SUCCESS' and result.items==[]