"""Auditable raw-response archive for Phase 2 collectors."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .models import utc_now


@dataclass(frozen=True)
class ArchiveReceipt:
    directory: Path
    payload_path: Path
    metadata_path: Path
    sha256: str


class RawArchive:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save(
        self,
        *,
        source: str,
        url: str,
        method: str,
        status: int | None,
        body: bytes,
        response_headers: Mapping[str, str] | None = None,
        encoding: str | None = None,
        error: str | None = None,
        collected_at: datetime | None = None,
    ) -> ArchiveReceipt:
        timestamp = collected_at or utc_now()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)

        digest = hashlib.sha256(body).hexdigest()
        source_slug = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-") or "unknown"
        parent = self.root / timestamp.date().isoformat() / source_slug
        parent.mkdir(parents=True, exist_ok=True)
        stem = f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{digest[:16]}"
        directory = parent / stem
        suffix = 1
        while directory.exists():
            directory = parent / f"{stem}-{suffix}"
            suffix += 1
        directory.mkdir()

        headers = {key.lower(): value for key, value in (response_headers or {}).items()}
        content_type = headers.get("content-type")
        payload_name = "response.html" if content_type and "html" in content_type.lower() else "response.bin"
        payload_path = directory / payload_name
        payload_path.write_bytes(body)

        metadata = {
            "url": url,
            "method": method.upper(),
            "status": status,
            "collected_at": timestamp.isoformat().replace("+00:00", "Z"),
            "content_type": content_type,
            "encoding": encoding,
            "byte_length": len(body),
            "sha256": digest,
            "error": error,
        }
        metadata_path = directory / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return ArchiveReceipt(directory, payload_path, metadata_path, digest)