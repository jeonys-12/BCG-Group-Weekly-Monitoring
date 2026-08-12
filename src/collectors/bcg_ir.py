"""Collector for Bamboo Capital Group official disclosure pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from ..http_client import HTTPClient
from ..models import Attachment, CollectorError, CollectorResult, CollectorStatus, NormalizedRecord, utc_now
from ..normalize import build_record, canonicalize_url, normalize_body, normalize_title, parse_source_date
from .base import CollectorParseError


@dataclass(frozen=True)
class BCGListItem:
    published_date: date
    title: str
    url: str


class BCGIRCollector:
    source_name = "BCG IR"
    company_name = "BCG"

    def __init__(self, http: HTTPClient, config: dict) -> None:
        self.http = http
        self.base_url = str(config["base_url"])
        self.url_template = str(config["disclosure_url_template"])
        self.default_max_pages = int(config.get("max_pages", 10))

    def collect(
        self,
        start_date: date,
        end_date: date,
        *,
        max_pages: int | None = None,
    ) -> CollectorResult:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        page_limit = max_pages if max_pages is not None else self.default_max_pages
        if page_limit < 1:
            raise ValueError("max_pages must be at least 1")

        collected_at = utc_now()
        records: list[NormalizedRecord] = []
        errors: list[CollectorError] = []
        visited: list[str] = []
        list_successes = 0
        seen_urls: set[str] = set()

        for year in range(end_date.year, start_date.year - 1, -1):
            first_url = self.url_template.format(year=year)
            try:
                first_html, resolved_url = self._fetch(first_url, visited)
                first_items, available_pages = self.parse_list_page(first_html, resolved_url)
                list_successes += 1
            except Exception as exc:
                errors.append(CollectorError("LIST_FETCH_OR_PARSE_FAILED", str(exc), first_url))
                continue

            pages_to_visit = min(max(available_pages), page_limit)
            page_items = list(first_items)
            for page_number in range(2, pages_to_visit + 1):
                page_url = self._with_page(first_url, page_number)
                try:
                    html, resolved_page_url = self._fetch(page_url, visited)
                    parsed_items, _ = self.parse_list_page(html, resolved_page_url)
                    page_items.extend(parsed_items)
                except Exception as exc:
                    errors.append(CollectorError("LIST_PAGE_FAILED", str(exc), page_url))
                    break

            for list_item in page_items:
                if not start_date <= list_item.published_date <= end_date:
                    continue
                canonical_url = canonicalize_url(list_item.url, self.base_url)
                if canonical_url in seen_urls:
                    continue
                seen_urls.add(canonical_url)
                try:
                    detail_html, detail_url = self._fetch(canonical_url, visited)
                    record = self.parse_detail_page(
                        detail_html,
                        detail_url,
                        fallback=list_item,
                        collected_at=collected_at,
                    )
                except Exception as exc:
                    errors.append(CollectorError("DETAIL_FETCH_OR_PARSE_FAILED", str(exc), canonical_url))
                    record = build_record(
                        published_date=list_item.published_date,
                        company=self.company_name,
                        source=self.source_name,
                        title_original=list_item.title,
                        content_original=list_item.title,
                        url=canonical_url,
                        collected_at=collected_at,
                    )
                records.append(record)

        status = self._status(list_successes, errors)
        return CollectorResult(
            source=self.source_name,
            status=status,
            items=records,
            errors=errors,
            requested_range=(start_date, end_date),
            visited_urls=visited,
            collected_at=collected_at,
        )

    def _fetch(self, url: str, visited: list[str]) -> tuple[str, str]:
        response = self.http.get(url, archive_source=self.source_name)
        visited.append(response.url)
        response.raise_for_status()
        return response.text, response.url

    @staticmethod
    def _with_page(url: str, page_number: int) -> str:
        parts = urlsplit(url)
        query = parse_qs(parts.query, keep_blank_values=True)
        query["pagenumber"] = [str(page_number)]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), ""))

    @staticmethod
    def parse_list_page(html: str, page_url: str) -> tuple[list[BCGListItem], set[int]]:
        soup = BeautifulSoup(html, "lxml")
        container = soup.select_one(".congbothongtin-list:not(.detail)")
        if container is None:
            raise CollectorParseError("BCG disclosure list container is missing")

        items: list[BCGListItem] = []
        for row in container.select("li"):
            link = row.select_one("a[href]")
            time_node = row.select_one("time")
            if link is None or time_node is None:
                continue
            title = normalize_title(link.get("title") or link.get_text(" ", strip=True))
            if not title:
                continue
            items.append(
                BCGListItem(
                    published_date=parse_source_date(time_node.get_text(" ", strip=True)),
                    title=title,
                    url=canonicalize_url(link["href"], page_url),
                )
            )

        pages = {1}
        for link in soup.select('a[href*="pagenumber="]'):
            values = parse_qs(urlsplit(link.get("href", "")).query).get("pagenumber", [])
            for value in values:
                if value.isdigit():
                    pages.add(int(value))
        return items, pages

    def parse_detail_page(
        self,
        html: str,
        page_url: str,
        *,
        fallback: BCGListItem,
        collected_at: datetime,
    ) -> NormalizedRecord:
        soup = BeautifulSoup(html, "lxml")
        container = soup.select_one(".congbothongtin-list.detail")
        if container is None:
            raise CollectorParseError("BCG disclosure detail container is missing")
        title_node = container.select_one("h2.title-child")
        date_node = container.select_one("h3")
        body_node = container.select_one(".content")
        if title_node is None or body_node is None:
            raise CollectorParseError("BCG disclosure detail title/body is missing")

        date_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", date_node.get_text(" ", strip=True) if date_node else "")
        published = parse_source_date(date_match.group(0)) if date_match else fallback.published_date
        body_lines = [node.get_text(" ", strip=True) for node in body_node.select("p, li")]
        content = normalize_body("\n".join(line for line in body_lines if line))
        attachments: list[Attachment] = []
        seen: set[str] = set()
        for link in body_node.select("a[href]"):
            href = canonicalize_url(link["href"], page_url)
            if href in seen or not re.search(r"\.(?:pdf|docx?|xlsx?)(?:$|\?)", href, re.IGNORECASE):
                continue
            seen.add(href)
            label = normalize_title(link.get_text(" ", strip=True)) or href.rsplit("/", 1)[-1]
            attachments.append(Attachment(label, href, None))

        return build_record(
            published_date=published,
            company=self.company_name,
            source=self.source_name,
            title_original=title_node.get_text(" ", strip=True),
            content_original=content,
            url=page_url,
            base_url=self.base_url,
            attachments=attachments,
            collected_at=collected_at,
        )

    @staticmethod
    def _status(list_successes: int, errors: list[CollectorError]) -> CollectorStatus:
        if list_successes == 0:
            return CollectorStatus.FAILED
        if errors:
            return CollectorStatus.PARTIAL
        return CollectorStatus.SUCCESS