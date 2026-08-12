"""Typed Phase 2 data contracts for official disclosure collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any


SCHEMA_FIELDS = (
    "id",
    "published_date",
    "collected_date",
    "company",
    "source",
    "source_type",
    "title_original",
    "title_ko",
    "content_original",
    "summary_ko",
    "url",
    "document_number",
    "category",
    "importance",
    "hanwha_relevance",
    "sssg_relevance",
    "risk_direction",
    "is_duplicate",
    "duplicate_of",
    "excel_included",
    "review_status",
    "created_at",
    "attachments",
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class CollectorStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Attachment:
    title: str
    url: str
    content_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedRecord:
    id: str
    published_date: str
    collected_date: str
    company: str
    source: str
    source_type: str
    title_original: str
    title_ko: str | None
    content_original: str
    summary_ko: str | None
    url: str
    document_number: str | None
    category: str | None
    importance: str | None
    hanwha_relevance: str | None
    sssg_relevance: str | None
    risk_direction: str | None
    is_duplicate: bool
    duplicate_of: str | None
    excel_included: bool
    review_status: str | None
    created_at: str
    attachments: tuple[Attachment, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attachments"] = [attachment.to_dict() for attachment in self.attachments]
        return payload


@dataclass(frozen=True)
class CollectorError:
    code: str
    message: str
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CollectorResult:
    source: str
    status: CollectorStatus
    items: list[NormalizedRecord]
    errors: list[CollectorError]
    requested_range: tuple[date, date]
    visited_urls: list[str]
    collected_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        start_date, end_date = self.requested_range
        return {
            "source": self.source,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "errors": [error.to_dict() for error in self.errors],
            "requested_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "visited_urls": list(self.visited_urls),
            "collected_at": self.collected_at.astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }