import os
from datetime import date
from pathlib import Path
import pytest,yaml
from src.archive import RawArchive
from src.collectors import HNXCollector,HOSECollector,SSCCollector
from src.http_client import HTTPClient,HTTPConfig
pytestmark=[pytest.mark.integration,pytest.mark.skipif(os.environ.get('RUN_LIVE_TESTS')!='1',reason='set RUN_LIVE_TESTS=1 to contact official websites')]
def test_bounded_phase3_live_contracts(tmp_path):
    config=yaml.safe_load(Path('config/sources.yaml').read_text(encoding='utf-8')); hc=dict(config['http']); hc['min_request_interval_seconds']=0.25; http=HTTPClient(HTTPConfig.from_mapping(hc),archive=RawArchive(tmp_path/'raw'))
    try: results=[c(http,config['sources'][k]).collect(date(2026,8,7),date(2026,8,7),max_pages=1) for c,k in [(HNXCollector,'hnx'),(HOSECollector,'hose'),(SSCCollector,'ssc')]]
    finally: http.close()
    assert all(r.visited_urls for r in results)