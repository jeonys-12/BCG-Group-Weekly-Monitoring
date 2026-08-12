"""Bounded HTTP client with GET-only retries, pacing, and raw archiving."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .archive import RawArchive


@dataclass(frozen=True)
class HTTPConfig:
    user_agent: str
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 30.0
    max_retries: int = 2
    min_request_interval_seconds: float = 1.0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "HTTPConfig":
        return cls(
            user_agent=str(value["user_agent"]),
            connect_timeout_seconds=float(value.get("connect_timeout_seconds", 10)),
            read_timeout_seconds=float(value.get("read_timeout_seconds", 30)),
            max_retries=int(value.get("max_retries", 2)),
            min_request_interval_seconds=float(value.get("min_request_interval_seconds", 1.0)),
        )


class HTTPClient:
    def __init__(
        self,
        config: HTTPConfig,
        *,
        archive: RawArchive | None = None,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.archive = archive
        self.session = session or requests.Session()
        self.sleeper = sleeper
        self.clock = clock
        self._last_request_at: float | None = None

        retry = Retry(
            total=config.max_retries,
            connect=config.max_retries,
            read=config.max_retries,
            status=config.max_retries,
            allowed_methods=frozenset({"GET"}),
            status_forcelist=(429, 500, 502, 503, 504),
            backoff_factor=0.5,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({"User-Agent": config.user_agent})

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        archive_source: str | None = None,
    ) -> requests.Response:
        self._pace()
        try:
            response = self.session.get(
                url,
                headers=dict(headers or {}),
                timeout=(
                    self.config.connect_timeout_seconds,
                    self.config.read_timeout_seconds,
                ),
            )
        except requests.RequestException as exc:
            if self.archive is not None and archive_source:
                self.archive.save(
                    source=archive_source,
                    url=url,
                    method="GET",
                    status=None,
                    body=b"",
                    error=f"{type(exc).__name__}: {exc}",
                )
            raise

        if self.archive is not None and archive_source:
            self.archive.save(
                source=archive_source,
                url=response.url,
                method="GET",
                status=response.status_code,
                body=response.content,
                response_headers=response.headers,
                encoding=response.encoding,
            )
        return response

    def post_form(self, url: str, *, data: Mapping[str, str], headers: Mapping[str, str] | None = None, archive_source: str | None = None) -> requests.Response:
        """Send one non-retried form POST for HNX read-only pagination."""
        self._pace()
        try:
            response = self.session.post(url, data=dict(data), headers=dict(headers or {}), timeout=(self.config.connect_timeout_seconds, self.config.read_timeout_seconds))
        except requests.RequestException as exc:
            if self.archive is not None and archive_source:
                self.archive.save(source=archive_source, url=url, method="POST", status=None, body=b"", error=f"{type(exc).__name__}: {exc}")
            raise
        if self.archive is not None and archive_source:
            self.archive.save(source=archive_source, url=response.url, method="POST", status=response.status_code, body=response.content, response_headers=response.headers, encoding=response.encoding)
        return response

    def _pace(self) -> None:
        now = self.clock()
        if self._last_request_at is not None:
            remaining = self.config.min_request_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self.sleeper(remaining)
                now = self.clock()
        self._last_request_at = now

    def close(self) -> None:
        self.session.close()