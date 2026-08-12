from __future__ import annotations

from pathlib import Path
from typing import Mapping

import requests


class FakeResponse:
    def __init__(self, url: str, text: str, status_code: int = 200) -> None:
        self.url = url
        self.text = text
        self.status_code = status_code
        self.content = text.encode("utf-8")
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code} for {self.url}")


class FixtureHTTPClient:
    def __init__(self, responses: Mapping[str, str | Path | FakeResponse]) -> None:
        self.responses = dict(responses)
        self.calls: list[tuple[str, dict[str, str], str | None]] = []
        self.closed = False

    def get(self, url: str, *, headers=None, archive_source=None) -> FakeResponse:
        self.calls.append((url, dict(headers or {}), archive_source))
        if url not in self.responses:
            raise requests.ConnectionError(f"No fixture response configured for {url}")
        value = self.responses[url]
        if isinstance(value, FakeResponse):
            return value
        if isinstance(value, Path):
            text = value.read_text(encoding="utf-8")
        else:
            text = value
        return FakeResponse(url, text)

    def close(self) -> None:
        self.closed = True