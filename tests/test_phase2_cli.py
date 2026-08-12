from __future__ import annotations

import json
from pathlib import Path

import yaml

from src import main as main_module
from tests.helpers import FixtureHTTPClient


BCG = "https://bamboocap.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/2026"
LAND = "https://www.bcgland.com.vn/vi/quan-he-dau-tu/cong-bo-thong-tin"


def fixture(source: str, name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "collectors" / source / name


def test_fixture_based_end_to_end_cli(monkeypatch, tmp_path) -> None:
    http = FixtureHTTPClient(
        {
            BCG: fixture("bcg_ir", "list_page_1.html"),
            f"{BCG}/cong-van-7330": fixture("bcg_ir", "detail_7330.html"),
            f"{BCG}/thong-bao-huy-tu-cach": fixture("bcg_ir", "detail_notice.html"),
            LAND: fixture("bcg_land_ir", "shell.html"),
            f"{LAND}/2026": fixture("bcg_land_ir", "year_2026.html"),
        }
    )
    monkeypatch.setattr(main_module, "HTTPClient", lambda *args, **kwargs: http)

    config = {
        "http": {
            "user_agent": "test-agent",
            "connect_timeout_seconds": 1,
            "read_timeout_seconds": 1,
            "max_retries": 0,
            "min_request_interval_seconds": 0,
        },
        "archive_root": str(tmp_path / "raw"),
        "sources": {
            "bcg_ir": {
                "enabled": True,
                "base_url": "https://bamboocap.com.vn",
                "disclosure_url_template": "https://bamboocap.com.vn/quan-he-nha-dau-tu/cong-bo-thong-tin/{year}",
                "max_pages": 1,
            },
            "bcg_land_ir": {
                "enabled": True,
                "base_url": "https://www.bcgland.com.vn",
                "disclosure_url": LAND,
                "disclosure_year_url_template": f"{LAND}/{{year}}",
                "max_pages": 1,
            },
        },
    }
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    output = tmp_path / "normalized.json"

    exit_code = main_module.main(
        [
            "--config",
            str(config_path),
            "--start",
            "2026-08-06",
            "--end",
            "2026-08-07",
            "--max-pages",
            "1",
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["status"] == "SUCCESS"
    assert [source["status"] for source in payload["sources"]] == ["SUCCESS", "SUCCESS"]
    assert sum(len(source["items"]) for source in payload["sources"]) == 4
    assert http.closed