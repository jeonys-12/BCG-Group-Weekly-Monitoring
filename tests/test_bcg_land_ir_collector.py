from __future__ import annotations

from datetime import date
from pathlib import Path

from src.collectors.bcg_land_ir import BCGLandIRCollector
from src.models import CollectorStatus
from tests.helpers import FixtureHTTPClient


BASE = "https://www.bcgland.com.vn"
SHELL = f"{BASE}/vi/quan-he-dau-tu/cong-bo-thong-tin"
YEAR = f"{SHELL}/2026"


def fixture(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "collectors" / "bcg_land_ir" / name


def make_collector(responses: dict) -> tuple[BCGLandIRCollector, FixtureHTTPClient]:
    http = FixtureHTTPClient(responses)
    collector = BCGLandIRCollector(
        http,
        {
            "base_url": BASE,
            "disclosure_url": SHELL,
            "disclosure_year_url_template": f"{SHELL}/{{year}}",
            "max_pages": 10,
        },
    )
    return collector, http


def test_bcg_land_collector_uses_ajax_year_endpoint_and_preserves_pdf() -> None:
    collector, http = make_collector(
        {SHELL: fixture("shell.html"), YEAR: fixture("year_2026.html")}
    )
    result = collector.collect(date(2026, 8, 6), date(2026, 8, 7), max_pages=1)

    assert result.status is CollectorStatus.SUCCESS
    assert [item.published_date for item in result.items] == ["2026-08-07", "2026-08-06"]
    assert result.items[0].title_original.startswith("Công văn 7331")
    assert result.items[0].url == f"{BASE}/pdf/20260807-bcr.pdf"
    assert result.items[0].attachments[0].url == result.items[0].url
    year_call = next(call for call in http.calls if call[0] == YEAR)
    assert year_call[1] == {"X-Requested-With": "XMLHttpRequest"}


def test_empty_static_shell_is_explicit_failure() -> None:
    collector, _ = make_collector({SHELL: fixture("empty_shell.html")})
    result = collector.collect(date(2026, 8, 6), date(2026, 8, 7), max_pages=1)
    assert result.status is CollectorStatus.FAILED
    assert not result.items
    assert result.errors[0].code == "SHELL_FETCH_OR_PARSE_FAILED"


def test_changed_ajax_schema_is_explicit_failure() -> None:
    collector, _ = make_collector(
        {SHELL: fixture("shell.html"), YEAR: fixture("malformed_year.html")}
    )
    result = collector.collect(date(2026, 8, 6), date(2026, 8, 7), max_pages=1)
    assert result.status is CollectorStatus.FAILED
    assert not result.items
    assert result.errors[0].code == "YEAR_FETCH_OR_PARSE_FAILED"