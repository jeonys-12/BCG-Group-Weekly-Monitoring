"""Collector for BCG Land official AJAX disclosure fragments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from ..http_client import HTTPClient
from ..models import Attachment, CollectorError, CollectorResult, CollectorStatus, NormalizedRecord, utc_now
from ..normalize import build_record, canonicalize_url, normalize_title, parse_source_date
from .base import CollectorParseError


@dataclass(frozen=True)
class BCGLandListItem:
    published_date: date
    title: str
    url: str


class BCGLandIRCollector:
    source_name = "BCG Land IR"
    company_name = "BCG Land"

    def __init__(self, http: HTTPClient, config: dict) -> None:
        self.http = http
        self.base_url = str(config["base_url"])
        self.disclosure_url = str(config["disclosure_url"])
        self.year_url_template = str(config["disclosure_year_url_template"])
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
        successful_years = 0

        try:
            shell_html, shell_url = self._fetch(self.disclosure_url, visited, ajax=False)
            year_urls = self.parse_shell_year_urls(shell_html, shell_url)
        except Exception as exc:
            return CollectorResult(
                source=self.source_name,
                status=CollectorStatus.FAILED,
                items=[],
                errors=[CollectorError("SHELL_FETCH_OR_PARSE_FAILED", str(exc), self.disclosure_url)],
                requested_range=(start_date, end_date),
                visited_urls=visited,
                collected_at=collected_at,
            )

        requested_years = list(range(end_date.year, start_date.year - 1, -1))[:page_limit]
        for year in requested_years:
            year_url = year_urls.get(year, self.year_url_template.format(year=year))
            try:
                fragment, resolved_url = self._fetch(year_url, visited, ajax=True)
                year_items = self.parse_year_fragment(fragment, resolved_url)
                successful_years += 1
            except Exception as exc:
                errors.append(CollectorError("YEAR_FETCH_OR_PARSE_FAILED", str(exc), year_url))
                continue

            for item in year_items:
                if not start_date <= item.published_date <= end_date:
                    continue
                attachment = Attachment(item.title, item.url, "application/pdf" if ".pdf" in item.url.lower() else None)
                records.append(
                    build_record(
                        published_date=item.published_date,
                        company=self.company_name,
                        source=self.source_name,
                        title_original=item.title,
                        content_original=item.title,
                        url=item.url,
                        base_url=self.base_url,
                        attachments=[attachment],
                        collected_at=collected_at,
                    )
                )

        if successful_years == 0:
            status = CollectorStatus.FAILED
        elif errors:
            status = CollectorStatus.PARTIAL
        else:
            status = CollectorStatus.SUCCESS
        return CollectorResult(
            source=self.source_name,
            status=status,
            items=records,
            errors=errors,
            requested_range=(start_date, end_date),
            visited_urls=visited,
            collected_at=collected_at,
        )

    def _fetch(self, url: str, visited: list[str], *, ajax: bool) -> tuple[str, str]:
        headers = {"X-Requested-With": "XMLHttpRequest"} if ajax else None
        response = self.http.get(url, headers=headers, archive_source=self.source_name)
        visited.append(response.url)
        response.raise_for_status()
        return response.text, response.url

    @staticmethod
    def parse_shell_year_urls(html: str, page_url: str) -> dict[int, str]:
        soup = BeautifulSoup(html, "lxml")
        root = soup.select_one('.shareholder-loading[data-sub-shareholder="410"]')
        if root is None:
            raise CollectorParseError("BCG Land disclosure shell marker is missing")
        years: dict[int, str] = {}
        for node in root.select(".num-report[data-href]"):
            text = normalize_title(node.get_text(" ", strip=True))
            if text.isdigit() and len(text) == 4:
                years[int(text)] = canonicalize_url(node["data-href"], page_url)
        if not years:
            raise CollectorParseError("BCG Land disclosure year endpoints are missing")
        return years

    @staticmethod
    def parse_year_fragment(html: str, page_url: str) -> list[BCGLandListItem]:
        soup = BeautifulSoup(html, "lxml")
        root = soup.select_one(".slide-report")
        if root is None:
            raise CollectorParseError("BCG Land AJAX disclosure fragment marker is missing")
        items: list[BCGLandListItem] = []
        for row in root.select(".list-box"):
            link = row.select_one("a[href]")
            date_node = row.select_one(".date")
            title_node = row.select_one(".r-text p")
            if link is None or date_node is None or title_node is None:
                raise CollectorParseError("BCG Land disclosure row is missing URL, date, or title")
            items.append(
                BCGLandListItem(
                    published_date=parse_source_date(date_node.get_text(" ", strip=True)),
                    title=normalize_title(title_node.get_text(" ", strip=True)),
                    url=canonicalize_url(link["href"], page_url),
                )
            )
        return items