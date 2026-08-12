"""Bounded Phase 2 collection CLI. No classification or Excel writing occurs here."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Sequence

import yaml

from .archive import RawArchive
from .collectors import BCGIRCollector, BCGLandIRCollector
from .http_client import HTTPClient, HTTPConfig
from .models import CollectorResult, CollectorStatus


def load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict) or "http" not in payload or "sources" not in payload:
        raise ValueError("sources config must contain http and sources mappings")
    return payload


def build_collectors(config: dict, http: HTTPClient) -> list:
    collectors = []
    source_config = config["sources"]
    if source_config.get("bcg_ir", {}).get("enabled", False):
        collectors.append(BCGIRCollector(http, source_config["bcg_ir"]))
    if source_config.get("bcg_land_ir", {}).get("enabled", False):
        collectors.append(BCGLandIRCollector(http, source_config["bcg_land_ir"]))
    return collectors


def run_collection(
    config: dict,
    *,
    start_date: date,
    end_date: date,
    max_pages: int | None = None,
) -> dict:
    archive = RawArchive(config.get("archive_root", "data/raw"))
    http = HTTPClient(HTTPConfig.from_mapping(config["http"]), archive=archive)
    try:
        results: list[CollectorResult] = [
            collector.collect(start_date, end_date, max_pages=max_pages)
            for collector in build_collectors(config, http)
        ]
    finally:
        http.close()

    if not results or all(result.status is CollectorStatus.FAILED for result in results):
        overall_status = CollectorStatus.FAILED.value
    elif any(result.status is not CollectorStatus.SUCCESS for result in results):
        overall_status = CollectorStatus.PARTIAL.value
    else:
        overall_status = CollectorStatus.SUCCESS.value
    return {
        "status": overall_status,
        "requested_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "sources": [result.to_dict() for result in results],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect official BCG and BCG Land disclosures")
    parser.add_argument("--config", default="config/sources.yaml")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.start > args.end:
        raise SystemExit("--start must not be after --end")
    config = load_config(args.config)
    payload = run_collection(
        config,
        start_date=args.start,
        end_date=args.end,
        max_pages=args.max_pages,
    )
    output = args.output or Path("data/processed") / f"{args.end.isoformat()}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 2 if payload["status"] == CollectorStatus.FAILED.value else 0


if __name__ == "__main__":
    raise SystemExit(main())