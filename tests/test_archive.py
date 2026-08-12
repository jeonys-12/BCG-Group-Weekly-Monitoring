from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from src.archive import RawArchive


def test_raw_archive_writes_payload_and_safe_audit_metadata(tmp_path) -> None:
    body = b"<html>official response</html>"
    receipt = RawArchive(tmp_path).save(
        source="BCG IR",
        url="https://example.com/disclosure",
        method="GET",
        status=200,
        body=body,
        response_headers={
            "Content-Type": "text/html; charset=utf-8",
            "Set-Cookie": "secret-cookie",
            "Authorization": "Bearer secret",
        },
        encoding="utf-8",
        collected_at=datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc),
    )
    assert receipt.payload_path.name == "response.html"
    assert receipt.payload_path.read_bytes() == body
    metadata_text = receipt.metadata_path.read_text(encoding="utf-8")
    metadata = json.loads(metadata_text)
    assert metadata["sha256"] == hashlib.sha256(body).hexdigest()
    assert metadata["byte_length"] == len(body)
    assert metadata["status"] == 200
    assert "cookie" not in metadata_text.lower()
    assert "authorization" not in metadata_text.lower()
    assert "secret" not in metadata_text.lower()


def test_binary_archive_uses_response_bin(tmp_path) -> None:
    receipt = RawArchive(tmp_path).save(
        source="BCG Land IR",
        url="https://example.com/file.pdf",
        method="GET",
        status=200,
        body=b"%PDF",
        response_headers={"Content-Type": "application/pdf"},
    )
    assert receipt.payload_path.name == "response.bin"