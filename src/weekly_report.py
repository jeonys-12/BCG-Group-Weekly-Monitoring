"""Weekly BCG/BCG Land collection-to-Excel pipeline for local scheduling."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from .excel_writer import TrendItem, append_trends, load_rules
from .main import load_config, run_collection
from .models import CollectorStatus


ALLOWED_SOURCES = frozenset({"BCG IR", "BCG Land IR"})


class WeeklyReportError(RuntimeError):
    """Raised when a weekly workbook cannot be produced safely."""


def completed_week(run_date: date) -> tuple[date, date]:
    """Return the last completed Monday-Sunday window before run_date."""

    report_end = run_date - timedelta(days=run_date.weekday() + 1)
    return report_end - timedelta(days=6), report_end


def _trend_from_record(record: dict[str, Any]) -> TrendItem:
    source = str(record.get("source", "")).strip()
    if source not in ALLOWED_SOURCES:
        raise WeeklyReportError(f"Unsupported weekly source: {source!r}")
    summary = (
        str(record.get("summary_ko") or "").strip()
        or str(record.get("title_ko") or "").strip()
        or str(record.get("title_original") or "").strip()
    )
    if not summary:
        raise WeeklyReportError("A collected record has no usable source-derived title")
    note = str(record.get("document_number") or "").strip()
    return TrendItem.from_mapping(
        {
            "published_date": record["published_date"],
            "source": source,
            "summary_ko": summary,
            "note": note,
            "url": str(record.get("url") or "").strip(),
        }
    )


def records_to_trends(payload: dict[str, Any]) -> list[TrendItem]:
    """Flatten source results and suppress exact stable-ID repeats."""

    trends: list[TrendItem] = []
    seen_ids: set[str] = set()
    for source_result in payload.get("sources", []):
        source_name = str(source_result.get("source", ""))
        if source_name not in ALLOWED_SOURCES:
            raise WeeklyReportError(f"Excluded source appeared in collection output: {source_name!r}")
        for record in source_result.get("items", []):
            record_id = str(record.get("id") or "").strip()
            if not record_id:
                raise WeeklyReportError("A collected record has no deterministic ID")
            if record_id in seen_ids:
                continue
            seen_ids.add(record_id)
            trends.append(_trend_from_record(record))
    return trends


def _unique_output_path(
    output_dir: Path,
    report_start: date,
    report_end: date,
    generated_at: datetime,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"BCG_Group_Weekly_Trend_{report_start.isoformat()}_{report_end.isoformat()}"
    candidate = output_dir / f"{stem}.xlsx"
    if not candidate.exists():
        return candidate
    suffix = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = output_dir / f"{stem}_{suffix}.xlsx"
    counter = 2
    while candidate.exists():
        candidate = output_dir / f"{stem}_{suffix}_{counter}.xlsx"
        counter += 1
    return candidate


def _write_metadata(metadata_dir: Path, report_end: date, payload: dict[str, Any]) -> Path:
    metadata_dir.mkdir(parents=True, exist_ok=True)
    path = metadata_dir / f"weekly-{report_end.isoformat()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate_weekly_report(
    *,
    sources_path: Path,
    rules_path: Path,
    template_path: Path,
    output_dir: Path,
    metadata_dir: Path,
    report_start: date,
    report_end: date,
    max_pages: int | None = None,
    collector: Callable[..., dict[str, Any]] = run_collection,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Collect official IR records and create one append-only weekly workbook."""

    if report_start > report_end:
        raise ValueError("report_start must not be after report_end")
    timestamp = generated_at or datetime.now(timezone.utc)
    config = load_config(sources_path)
    collection = collector(
        config,
        start_date=report_start,
        end_date=report_end,
        max_pages=max_pages,
    )
    source_statuses = {
        str(result.get("source")): str(result.get("status"))
        for result in collection.get("sources", [])
    }
    errors = [
        {"source": result.get("source"), **error}
        for result in collection.get("sources", [])
        for error in result.get("errors", [])
    ]
    metadata: dict[str, Any] = {
        "generated_at": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "report_start": report_start.isoformat(),
        "report_end": report_end.isoformat(),
        "status": collection.get("status"),
        "source_statuses": source_statuses,
        "errors": errors,
        "output_path": None,
        "item_count": 0,
        "record_ids": [],
    }
    if collection.get("status") == CollectorStatus.FAILED.value:
        metadata_path = _write_metadata(metadata_dir, report_end, metadata)
        raise WeeklyReportError(f"All configured sources failed; metadata: {metadata_path}")

    trends = records_to_trends(collection)
    record_ids = [
        str(record["id"])
        for result in collection.get("sources", [])
        for record in result.get("items", [])
        if str(record.get("id") or "")
    ]
    output_path = _unique_output_path(output_dir, report_start, report_end, timestamp)
    append_trends(
        template_path,
        output_path,
        trends,
        load_rules(rules_path),
        report_start=report_start,
        report_end=report_end,
        allow_empty=True,
    )
    metadata.update(
        {
            "output_path": str(output_path.resolve()),
            "item_count": len(trends),
            "record_ids": list(dict.fromkeys(record_ids)),
        }
    )
    metadata_path = _write_metadata(metadata_dir, report_end, metadata)
    metadata["metadata_path"] = str(metadata_path.resolve())
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the weekly BCG IR Excel report")
    parser.add_argument("--sources", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--rules", type=Path, default=Path("config/report_rules.yaml"))
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("reports/template/BCG_Group_Trend_Master.xlsx"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/output"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("data/history"))
    parser.add_argument("--run-date", type=date.fromisoformat)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--max-pages", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if (args.start is None) != (args.end is None):
        raise SystemExit("--start and --end must be supplied together")
    if args.start is not None:
        report_start, report_end = args.start, args.end
    else:
        report_start, report_end = completed_week(args.run_date or date.today())
    try:
        result = generate_weekly_report(
            sources_path=args.sources,
            rules_path=args.rules,
            template_path=args.template,
            output_dir=args.output_dir,
            metadata_dir=args.metadata_dir,
            report_start=report_start,
            report_end=report_end,
            max_pages=args.max_pages,
        )
    except WeeklyReportError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
