"""Source-preserving normalization for official disclosure records."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

from dateutil import parser as date_parser

from .models import Attachment, NormalizedRecord, utc_now


_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
_REQUIRED_TEXT_FIELDS = ("source", "title_original", "url")


class NormalizationError(ValueError):
    """Raised when a source item cannot satisfy the normalized contract."""


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFC", value or "")


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", normalize_unicode(value)).strip()


def normalize_body(value: str) -> str:
    """Normalize inline whitespace while retaining paragraph and bullet lines."""

    normalized = normalize_unicode(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t ]+", " ", line).strip() for line in normalized.split("\n")]
    compact: list[str] = []
    for line in lines:
        if line or (compact and compact[-1]):
            compact.append(line)
    while compact and not compact[-1]:
        compact.pop()
    return "\n".join(compact)


def canonicalize_url(value: str, base_url: str | None = None) -> str:
    absolute = urljoin(base_url or "", normalize_unicode(value).strip())
    parts = urlsplit(absolute)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise NormalizationError(f"Unsupported or relative URL without a base: {value!r}")
    filtered_query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_KEYS and not key.lower().startswith("utm_")
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~"),
            urlencode(filtered_query, doseq=True),
            "",
        )
    )


def parse_source_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = normalize_title(value)
    if not text:
        raise NormalizationError("Published date is empty")

    iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        return _validated_date(year, month, day, text)

    dmy_match = re.fullmatch(r"(\d{1,2})\s*(?:/|-|\.)\s*(\d{1,2})\s*(?:/|-)\s*(\d{4})", text)
    if not dmy_match:
        dmy_match = re.fullmatch(r"(\d{1,2})\s+(\d{1,2})\s*-\s*(\d{4})", text)
    if dmy_match:
        day, month, year = map(int, dmy_match.groups())
        return _validated_date(year, month, day, text)

    vietnamese_match = re.search(
        r"(?:ngay\s+)?(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})",
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower(),
    )
    if vietnamese_match:
        day, month, year = map(int, vietnamese_match.groups())
        return _validated_date(year, month, day, text)

    if re.search(r"[A-Za-z]", text):
        try:
            return date_parser.parse(text, dayfirst=True, fuzzy=False).date()
        except (ValueError, OverflowError) as exc:
            raise NormalizationError(f"Invalid published date: {text!r}") from exc

    raise NormalizationError(f"Ambiguous or unsupported published date: {text!r}")


def _validated_date(year: int, month: int, day: int, original: str) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise NormalizationError(f"Invalid published date: {original!r}") from exc


def extract_document_number(*values: str) -> str | None:
    text = " ".join(normalize_title(value) for value in values if value)
    pattern = re.compile(
        r"(?:Cong\s+van|Công\s+văn|So|Số|No\.?|Official\s+Letter)\s*"
        r"(?:so\s*|số\s*)?([0-9]{1,6}(?:/[A-Z0-9Đ._-]+)*)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    return normalize_title(match.group(1)) if match else None


def stable_record_id(
    *,
    source: str,
    url: str,
    document_number: str | None,
    published_date: date,
    title_original: str,
) -> str:
    identity = {
        "source": normalize_title(source),
        "url": canonicalize_url(url),
        "document_number": normalize_title(document_number or ""),
        "published_date": published_date.isoformat(),
        "title_original": normalize_title(title_original),
    }
    serialized = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_record(
    *,
    published_date: str | date | datetime,
    company: str,
    source: str,
    title_original: str,
    content_original: str,
    url: str,
    base_url: str | None = None,
    document_number: str | None = None,
    attachments: list[Attachment] | tuple[Attachment, ...] = (),
    collected_at: datetime | None = None,
) -> NormalizedRecord:
    timestamp = collected_at or utc_now()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)

    parsed_date = parse_source_date(published_date)
    normalized_title = normalize_title(title_original)
    normalized_url = canonicalize_url(url, base_url)
    normalized_source = normalize_title(source)
    normalized_company = normalize_title(company)
    normalized_document = normalize_title(document_number or "") or extract_document_number(
        normalized_title, content_original
    )

    required = {
        "source": normalized_source,
        "title_original": normalized_title,
        "url": normalized_url,
    }
    missing = [name for name in _REQUIRED_TEXT_FIELDS if not required[name]]
    if missing:
        raise NormalizationError(f"Missing required fields: {', '.join(missing)}")

    normalized_attachments = tuple(
        Attachment(
            title=normalize_title(attachment.title),
            url=canonicalize_url(attachment.url, base_url),
            content_type=attachment.content_type,
        )
        for attachment in attachments
    )
    created_at = timestamp.isoformat().replace("+00:00", "Z")
    return NormalizedRecord(
        id=stable_record_id(
            source=normalized_source,
            url=normalized_url,
            document_number=normalized_document,
            published_date=parsed_date,
            title_original=normalized_title,
        ),
        published_date=parsed_date.isoformat(),
        collected_date=timestamp.date().isoformat(),
        company=normalized_company,
        source=normalized_source,
        source_type="OFFICIAL_IR",
        title_original=normalized_title,
        title_ko=None,
        content_original=normalize_body(content_original),
        summary_ko=None,
        url=normalized_url,
        document_number=normalized_document,
        category=None,
        importance=None,
        hanwha_relevance=None,
        sssg_relevance=None,
        risk_direction=None,
        is_duplicate=False,
        duplicate_of=None,
        excel_included=False,
        review_status=None,
        created_at=created_at,
        attachments=normalized_attachments,
    )