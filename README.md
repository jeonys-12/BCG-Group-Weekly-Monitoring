# BCG Group Weekly Monitoring Automation

Phase 1 provides a conservative append-only Excel report engine. Phase 2 adds independent collectors for the official BCG and BCG Land investor-relations disclosures, raw-response archiving, source-preserving normalization, and a bounded JSON CLI.

Phase 2 intentionally does not perform deduplication, classification, translation, summarization, impact analysis, Excel insertion, or GitHub Actions orchestration.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Collect official disclosures

```powershell
.\.venv\Scripts\python.exe -m src.main `
  --config config/sources.yaml `
  --start 2026-08-06 `
  --end 2026-08-07 `
  --max-pages 1 `
  --output data/processed/2026-08-07.json
```

The CLI writes normalized JSON and archives every live response under the configured `archive_root`. A parser or network failure is reported as `PARTIAL` or `FAILED`; it is never converted into a successful empty result.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

All default tests use local fixtures and make no live network calls. To run the explicitly separated bounded live smoke test:

```powershell
$env:RUN_LIVE_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -m integration -q
```

## Excel safety

The approved Master is `reports/template/BCG_Group_Trend_Master.xlsx`. The writer never overwrites it. The source XLSB is analysis-only because Python libraries cannot safely round-trip its binary workbook structure and SoftCamp DRM envelope. See `docs/design.md` for the conversion and validation rationale.