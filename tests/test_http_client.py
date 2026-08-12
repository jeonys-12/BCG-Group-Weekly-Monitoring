from __future__ import annotations

from src.http_client import HTTPClient, HTTPConfig
from tests.helpers import FakeResponse


class FakeSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.adapters = {}
        self.calls = []
        self.closed = False

    def mount(self, prefix, adapter) -> None:
        self.adapters[prefix] = adapter

    def get(self, url, *, headers, timeout):
        self.calls.append((url, headers, timeout))
        return FakeResponse(url, "<html>ok</html>")

    def close(self) -> None:
        self.closed = True


def test_http_client_applies_user_agent_timeout_and_request_pacing() -> None:
    session = FakeSession()
    clock_values = iter([0.0, 0.25, 1.0])
    sleeps: list[float] = []
    client = HTTPClient(
        HTTPConfig(
            user_agent="test-agent",
            connect_timeout_seconds=2,
            read_timeout_seconds=3,
            max_retries=2,
            min_request_interval_seconds=1,
        ),
        session=session,
        clock=lambda: next(clock_values),
        sleeper=sleeps.append,
    )

    client.get("https://example.com/one")
    client.get("https://example.com/two", headers={"X-Test": "yes"})
    client.close()

    assert session.headers["User-Agent"] == "test-agent"
    assert session.calls[0][2] == (2, 3)
    assert session.calls[1][1] == {"X-Test": "yes"}
    assert sleeps == [0.75]
    assert session.closed
    retry = session.adapters["https://"].max_retries
    assert retry.allowed_methods == frozenset({"GET"})
    assert 429 in retry.status_forcelist