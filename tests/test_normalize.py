from __future__ import annotations

import unicodedata
from datetime import datetime, timezone

import pytest

from src.models import Attachment, SCHEMA_FIELDS
from src.normalize import (
    NormalizationError,
    build_record,
    canonicalize_url,
    normalize_body,
    normalize_title,
    parse_source_date,
)


def test_date_parsing_supports_official_formats_and_rejects_invalid() -> None:
    assert parse_source_date("07/08/2026").isoformat() == "2026-08-07"
    assert parse_source_date("07 08 - 2026").isoformat() == "2026-08-07"
    assert parse_source_date("7 August 2026").isoformat() == "2026-08-07"
    with pytest.raises(NormalizationError):
        parse_source_date("2026/08/07")
    with pytest.raises(NormalizationError):
        parse_source_date("31/02/2026")


def test_unicode_whitespace_body_and_url_normalization() -> None:
    decomposed = unicodedata.normalize("NFD", "Công  văn")
    assert normalize_title(f"  {decomposed}\t7330 ") == "Công văn 7330"
    assert normalize_body(" First  paragraph \n\n - bullet   text \n") == "First paragraph\n\n- bullet text"
    url = canonicalize_url("/item?a=1&utm_source=x&b=2#top", "https://EXAMPLE.com/root")
    assert url == "https://example.com/item?a=1&b=2"
    assert canonicalize_url('/Data/my file.pdf', 'https://example.com') == (
        'https://example.com/Data/my%20file.pdf'
    )


def test_record_has_full_schema_and_stable_id_across_collection_times() -> None:
    kwargs = {
        "published_date": "07/08/2026",
        "company": "BCG",
        "source": "BCG IR",
        "title_original": "Công văn 7330",
        "content_original": "Official content",
        "url": "https://bamboocap.com.vn/item?utm_source=test",
        "attachments": [Attachment("PDF", "/file.pdf")],
        "base_url": "https://bamboocap.com.vn",
    }
    first = build_record(**kwargs, collected_at=datetime(2026, 8, 12, tzinfo=timezone.utc))
    second = build_record(**kwargs, collected_at=datetime(2026, 8, 13, tzinfo=timezone.utc))
    assert first.id == second.id
    assert tuple(first.to_dict()) == SCHEMA_FIELDS
    assert first.document_number == "7330"
    assert first.url == "https://bamboocap.com.vn/item"
    assert first.attachments[0].url == "https://bamboocap.com.vn/file.pdf"