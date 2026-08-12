import json
from pathlib import Path
import yaml
from src import main as main_module
from tests.helpers import FakeResponse
ROOT=Path(__file__).parent/'fixtures'/'collectors'
class JsonResponse(FakeResponse):
    def __init__(self,url,payload): super().__init__(url,json.dumps(payload)); self.headers={'Content-Type':'application/json'}
    def json(self): return json.loads(self.text)
class HTTP:
    def __init__(self): self.closed=False
    def get(self,url,**kwargs):
        if 'hnx.vn/vi-vn/m-' in url: return FakeResponse(url,(ROOT/'hnx'/'issuer.html').read_text(encoding='utf-8'))
        if 'api.hsx.vn' in url: return JsonResponse(url,json.loads((ROOT/'hose'/'news.json').read_text(encoding='utf-8')))
        if 'tintuc?' in url: return FakeResponse(url,(ROOT/'ssc'/'list.html').read_text(encoding='utf-8'))
        return FakeResponse(url,(ROOT/'ssc'/'detail.html').read_text(encoding='utf-8'))
    def post_form(self,url,**kwargs): return FakeResponse(url,(ROOT/'hnx'/'issuer.html').read_text(encoding='utf-8'))
    def close(self): self.closed=True
def test_phase3_fixture_cli_preserves_independent_sources(monkeypatch,tmp_path):
    config=yaml.safe_load(Path('config/sources.yaml').read_text(encoding='utf-8'))
    config['archive_root']=str(tmp_path/'raw'); config['sources']['bcg_ir']['enabled']=False; config['sources']['bcg_land_ir']['enabled']=False
    path=tmp_path/'sources.yaml'; path.write_text(yaml.safe_dump(config),encoding='utf-8'); output=tmp_path/'out.json'; http=HTTP(); monkeypatch.setattr(main_module,'HTTPClient',lambda *a,**k:http)
    code=main_module.main(['--config',str(path),'--start','2026-08-07','--end','2026-08-07','--max-pages','1','--output',str(output)])
    payload=json.loads(output.read_text(encoding='utf-8'))
    assert code==0 and payload['status']=='SUCCESS'
    assert [x['source'] for x in payload['sources']]==['HNX','HOSE','SSC']
    assert all(x['items'] for x in payload['sources']) and http.closed