"""Common collector protocol and parsing errors."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from ..models import CollectorResult


class CollectorParseError(RuntimeError):
    """Raised when an official response does not match the expected schema."""


class Collector(Protocol):
    source_name: str

    def collect(
        self,
        start_date: date,
        end_date: date,
        *,
        max_pages: int | None = None,
    ) -> CollectorResult:
        ...