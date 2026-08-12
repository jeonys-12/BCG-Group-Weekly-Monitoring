from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest
import yaml

from src.archive import RawArchive
from src.collectors import BCGIRCollector, BCGLandIRCollector
from src.http_client import HTTPClient, HTTPConfig
from src.models import CollectorStatus


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="set RUN_LIVE_TESTS=1 to contact official websites",
    ),
]


def test_bounded_live_official_collectors(tmp_path: Path) -> None:
    config = yaml.safe_load(Path("config/sources.yaml").read_text(encoding="utf-8"))
    http_config = dict(config["http"])
    http_config["min_request_interval_seconds"] = 0.25
    http = HTTPClient(HTTPConfig.from_mapping(http_config), archive=RawArchive(tmp_path / "raw"))
    try:
        collectors = [
            BCGIRCollector(http, config["sources"]["bcg_ir"]),
            BCGLandIRCollector(http, config["sources"]["bcg_land_ir"]),
        ]
        results = [
            collector.collect(date(2026, 8, 6), date(2026, 8, 7), max_pages=1)
            for collector in collectors
        ]
    finally:
        http.close()

    assert all(result.status is not CollectorStatus.FAILED for result in results)
    assert all(result.visited_urls for result in results)