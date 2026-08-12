from __future__ import annotations

from datetime import date
from pathlib import Path

from src.collectors.bcg_ir import BCGIRCollector
from src.models import CollectorStatus
from tests.helpers import FixtureHTTPClient


BASE = "https://bamboocap.com.vn"
LIST = f"{BASE}/quan-he-nha-dau-tu/cong-bo-thong-tin/2026"
PAGE_2 = f"{LIST}?pagenumber=2"
DETAIL_7330 = f"{LIST}/cong-van-7330"
DETAIL_NOTICE = f"{LIST}/thong-bao-huy-tu-cach"
DETAIL_BOND = f"{LIST}/bcg122006"


def fixture(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "collectors" / "bcg_ir" / name


def make_collector(responses: dict) -> tuple[BCGIRCollector, FixtureHTTPClient]:
    http = FixtureHTTPClient(responses)
    collector = BCGIRCollector(
        http,
        {
            "base_url": BASE,
            "disclosure_url_template": f"{BASE}/quan-he-nha-dau-tu/cong-bo-thong-tin/{{year}}",
            "max_pages": 10,
        },
    )
    return collector, http


def full_responses() -> dict:
    return {
        LIST: fixture("list_page_1.html"),
        PAGE_2: fixture("list_page_2.html"),
        DETAIL_7330: fixture("detail_7330.html"),
        DETAIL_NOTICE: fixture("detail_notice.html"),
        DETAIL_BOND: fixture("detail_bond.html"),
    }


def test_bcg_collector_parses_pagination_detail_and_attachment() -> None:
    collector, http = make_collector(full_responses())
    result = collector.collect(date(2026, 8, 5), date(2026, 8, 7), max_pages=2)

    assert result.status is CollectorStatus.SUCCESS
    assert [item.published_date for item in result.items] == ["2026-08-07", "2026-08-06", "2026-08-05"]
    assert PAGE_2 in [call[0] for call in http.calls]
    first = result.items[0]
    assert first.title_original.startswith("Công văn 7330")
    assert "Bamboo Capital" in first.content_original
    assert first.document_number == "7330"
    assert first.attachments[0].url == f"{BASE}/Data/Sites/1/media/2026/cv-7330.pdf"


def test_bcg_collector_honors_max_pages() -> None:
    collector, http = make_collector(full_responses())
    result = collector.collect(date(2026, 8, 5), date(2026, 8, 7), max_pages=1)
    assert result.status is CollectorStatus.SUCCESS
    assert len(result.items) == 2
    assert PAGE_2 not in [call[0] for call in http.calls]


def test_bcg_detail_failure_is_partial_not_silent_loss() -> None:
    responses = full_responses()
    responses.pop(DETAIL_NOTICE)
    collector, _ = make_collector(responses)
    result = collector.collect(date(2026, 8, 6), date(2026, 8, 7), max_pages=1)

    assert result.status is CollectorStatus.PARTIAL
    assert len(result.items) == 2
    assert result.items[1].content_original == result.items[1].title_original
    assert [error.code for error in result.errors] == ["DETAIL_FETCH_OR_PARSE_FAILED"]